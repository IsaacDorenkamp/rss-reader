from fbs_runtime import PUBLIC_SETTINGS
from PyQt5.QtWidgets import QMainWindow, QAction, QListView, QHBoxLayout, QWidget, QMessageBox, QStatusBar, QLabel
from PyQt5.QtCore import QCoreApplication, QThreadPool, QItemSelection, Qt

import datetime
import functools
import logging
import lxml.etree
import os
import pytz
import time
from typing import Dict, Iterable, List
import requests
import uuid

import config
from concurrency import tasks
import main
import models
from persist import app_data, caching, tasks as iotasks
from reader.api import rss, xml
from reader.api.rss import Channel
from ui.delegates import FeedItemDelegate
from ui.models import AggregateFeedModel

from . import constants, dialogs
from .views import ItemView


class MainApplication(QMainWindow):
	__ctx: main.MainApplicationContext
	tasks: QThreadPool
	channels: caching.ChannelMultiCache
	loaded_feeds: Dict[str, models.FeedDefinition]

	def __init__(self, ctx: main.MainApplicationContext, *args, **kw):
		super().__init__(*args, **kw)

		self.__ctx = ctx
		self.loaded_feeds = ctx.loaded_feeds.copy()
		self.executor = QThreadPool.globalInstance()
		self.channels = caching.ChannelMultiCache()

		self._setup_ui()
		self._setup()

	def _setup_ui(self):
		version = PUBLIC_SETTINGS['version']
		self.setWindowTitle(f"RSS Reader v{version}")

		self._setup_menubar()
		self._setup_toolbar()

		self.layout().setContentsMargins(0, 0, 0, 0)

		self.content_pane = QWidget()
		self.setCentralWidget(self.content_pane)

		top_layout = QHBoxLayout(spacing=0)
		top_layout.setContentsMargins(0, 0, 0, 0)
		self.content_pane.setLayout(top_layout)

		self.feed_aggregate = AggregateFeedModel(
			sort_by=lambda item: -(
				item.pub_date.timestamp() if item.pub_date else datetime.datetime.now(pytz.utc).timestamp()
			)
		)

		self.items = sidebar = QListView(self.content_pane)
		sidebar.setFixedWidth(300)
		sidebar.setItemDelegate(FeedItemDelegate(sidebar))
		sidebar.setModel(self.feed_aggregate)
		sidebar.selectionModel().selectionChanged.connect(self._change_item)

		self._content = ItemView(parent=self)
		self._content.setObjectName("item-view")
		self._content.setContentsMargins(0, 0, 0, 0)

		top_layout.addWidget(sidebar)
		top_layout.addWidget(self._content)

		self.status_bar = QStatusBar(parent=self)
		self.status = QLabel(text="Ready")
		self.status_bar.addPermanentWidget(self.status)
		self.setStatusBar(self.status_bar)

	def _setup(self):
		self.try_fetch(self.loaded_feeds.values(), autoselect=True)

	def _setup_menubar(self):
		menu_bar = self.menuBar()

		quit_action = QAction("Quit", self)
		quit_action.setShortcut("Ctrl+Q")
		quit_action.triggered.connect(self.exit_app)

		file = menu_bar.addMenu("&File")
		file.addAction(quit_action)

		self.menu_subscribe = new_feed = QAction("Subscribe to Feed", self)
		new_feed.setShortcut("Ctrl+N")
		new_feed.triggered.connect(self.start_new_feed)

		manage_feeds = QAction("Manage subscriptions...", self)
		manage_feeds.triggered.connect(self.show_manage_feeds)

		self.menu_refresh = refresh_feeds = QAction("Refresh all feeds", self)
		refresh_feeds.setShortcut("F5")
		refresh_feeds.triggered.connect(self.refresh_feeds)

		self.feed_menu = feeds = menu_bar.addMenu("F&eeds")
		feeds.addAction(new_feed)
		feeds.addAction(manage_feeds)
		feeds.addAction(refresh_feeds)

		show_about = QAction("About...", self)
		show_about.triggered.connect(self.show_about_dialog)
		
		about = menu_bar.addMenu("&About")
		about.addAction(show_about)
	
	def _setup_toolbar(self):
		toolbar = self.addToolBar("Feeds")
		toolbar.setMovable(False)

		self.toolbar_subscribe = add_action = QAction(constants.resources["icons/plus"], "Subscribe to Feed", self)
		add_action.triggered.connect(self.start_new_feed)
		toolbar.addAction(add_action)

		self.refresh_action = QAction(constants.resources["icons/refresh"], "&Refresh", self)
		self.refresh_action.triggered.connect(self.refresh_feeds)
		toolbar.addAction(self.refresh_action)
	
	def _change_item(self, selection: QItemSelection):
		indexes = selection.indexes()
		if indexes:
			index = indexes[0]
			item = index.data(role=Qt.DisplayRole)
			item.read = True

			# modify item metadata
			meta_idx = self.__ctx.app_meta.find_item(
				channel=item.channel.link,
				guid=item.guid.value if item.guid else None,
				title=item.title
			)
			if meta_idx >= 0:
				meta = self.__ctx.app_meta.items[meta_idx]
				meta.read = True
			else:
				meta = models.ItemMeta(
					channel=item.channel.link,
					guid=item.guid.value if item.guid else None,
					title=item.title if not item.guid else None,
					read=True,
				)
				self.__ctx.app_meta.items.append(meta)

			self._content.set_item(item)
		else:
			self._content.set_item(None)

	def start_new_feed(self):
		dialog = dialogs.NewFeed()
		dialog.new_feed.connect(self.new_feed)
		dialog.show()
		dialog.exec_()

	def show_manage_feeds(self):
		dialog = dialogs.ManageSubscriptions(list(self.loaded_feeds.values()))
		dialog.show()
		result = dialog.exec_()

		if result:
			self.remove_feeds(dialog.removed, self.__ctx.app_meta)

	def show_about_dialog(self):
		dialog = dialogs.AboutDialog()
		dialog.show()
		dialog.exec_()

	def refresh_feeds(self):
		self.disable_feed_actions()

		self.set_status("Refetching feeds...")
		batch = tasks.Batch([tasks.FetchTask(feed_definition.url) for feed_definition in self.loaded_feeds.values()])
		batch.complete.connect(self.on_fetch_batch)
		batch.start(self.executor)

	def new_feed(self, url):
		self.set_status("Fetching new feed...")
		task = tasks.FetchTask(url)
		task.signals.finished.connect(self.on_fetch_new)
		self.executor.start(task)

	def try_fetch(self, feed_definitions: Iterable[models.FeedDefinition], autoselect=False):
		"""
		Determine which which feeds should be re-fetched and which cached
		feeds should be relevant based upon their skip days, skip hours,
		and TTL (time to live). If autoselect is true, the UI will automatically
		select the latest feed item when they are loaded.
		"""

		now = datetime.datetime.now(pytz.utc)
		to_fetch: List[models.FeedDefinition] = []
		results: Dict[str, Channel] = {}

		# determine which cached entries should be used
		for feed_definition in feed_definitions:
			if not feed_definition.last_retrieved:
				to_fetch.append(feed_definition)
			else:
				# check if cached version exists
				cached = self.channels.get(feed_definition.cache_key)
				if not cached or cached is Channel.Invalid:
					to_fetch.append(feed_definition)
				else:
					cached.ref = feed_definition.url

					ttl = feed_definition.ttl or config.DEFAULT_TTL
					skip_days = feed_definition.skip_days or []
					skip_hours = feed_definition.skip_hours or []

					if now.weekday() in skip_days or now.hour in skip_hours:
						results[feed_definition.channel] = cached
					else:
						if now.timestamp() > feed_definition.last_retrieved + ttl:
							to_fetch.append(feed_definition)
						else:
							results[feed_definition.channel] = cached

		# fetch non-cached entries
		if to_fetch:
			self.set_status("Fetching feeds...")
			batch = tasks.Batch([tasks.FetchTask(feed_definition.url) for feed_definition in to_fetch])
			batch.complete.connect(functools.partial(self.on_fetch_batch, cached=results, autoselect=autoselect))
			batch.start(self.executor)
		elif results:
			self.on_fetch_batch([], cached=results, autoselect=autoselect)

	def on_fetch_new(self, result: tasks.TaskResult[Channel]):
		if result.error:
			if isinstance(result.error, requests.RequestException):
				self.show_error("Feed data could not be retrieved.")
			elif isinstance(result.error, (xml.XMLEntityError, rss.RSSError, lxml.etree.XMLSyntaxError)):
				self.show_error("Data does not represent a valid RSS feed.")
			else:
				logging.error("%s - %s" % (result.error.__class__.__name__, str(result.error)))
				self.show_error("An unknown error occurred.")
			return

		channel = result.data
		if channel.link in [feed.channel for feed in self.loaded_feeds.values()]:
			self.show_error("A feed for that site already exists!")
			return

		feed_definition = self.loaded_feeds.get(channel.link)
		if feed_definition:
			if feed_definition.cache_key:
				cache_key = feed_definition.cache_key
			else:
				cache_key = str(uuid.uuid4())
				feed_definition.cache_key = cache_key
		else:
			cache_key = str(uuid.uuid4())
			feed_definition = models.FeedDefinition.from_channel(channel)
			feed_definition.cache_key = cache_key
			self.loaded_feeds[channel.link] = feed_definition

		self.set_status("Saving feed list...")
		save_task = app_data.create_save_feeds_task(self.loaded_feeds.values())
		save_task.signals.finished.connect(lambda result: self._io_complete([result]))
		self.executor.start(save_task)

		self.channels.set(cache_key, channel, ex=(60 * 60 * 24 * 7))
		self.feed_aggregate.add(channel)

	def on_fetch_batch(self, results: List[tasks.TaskResult[Channel]], **kw):
		cached = kw.get('cached', None)
		if cached:
			for channel in cached.values():
				logging.info("using cached feed - {}".format(channel.link))
				self._apply_metadata(channel.items, self.__ctx.app_meta)
				self.feed_aggregate.add(channel)

		io_tasks = []
		for result in results:
			if result.error:
				# TODO: GUI Error Display
				logging.error("{}: {}".format(result.error.__class__.__name__, str(result.error)))
			else:
				result = result.data
				self._apply_metadata(result.items, self.__ctx.app_meta)

				if result.link in self.loaded_feeds:
					feed_def = self.loaded_feeds[result.link]
					feed_def.update(result)
				else:
					feed_def = models.FeedDefinition.from_channel(result)
					self.loaded_feeds[feed_def.url] = feed_def

				feed_def.last_retrieved = int(time.time())
				if not feed_def.cache_key:
					feed_def.cache_key = str(uuid.uuid4())

				io_tasks.append(iotasks.CacheTask(self.channels, feed_def.cache_key, result))

				self.feed_aggregate.add(result)
		
		if kw.get("autoselect", False):
			self.items.setCurrentIndex(self.feed_aggregate.index(0, 0))

		self.set_status("Saving feed list...")
		io_tasks.append(app_data.create_save_feeds_task(self.loaded_feeds.values()))

		io_batch = tasks.Batch(io_tasks)
		io_batch.complete.connect(self._io_complete)
		io_batch.start(self.executor)
	
	def _io_complete(self, results: tasks.TaskResult):
		for result in results:
			if result.error:
				logging.error("{}: {}".format(result.error.__class__.__name__, str(result.error)))
		
		self.set_status("Done.")
		self.enable_feed_actions()

	def _apply_metadata(self, items: List[rss.Item], metadata: models.AppMeta):
		for item in items:
			meta_idx = metadata.find_item(channel=item.channel.link, guid=item.guid.value if item.guid else None, title=item.title)
			if meta_idx >= 0:
				meta = metadata.items[meta_idx]
				item.read = meta.read
	
	def remove_feeds(self, channels: List[str], metadata: models.AppMeta):
		self.disable_feed_actions()

		self.feed_aggregate.remove_channels(channels)
		self.items.viewport().repaint()
		self.loaded_feeds = {key: value for (key, value) in self.loaded_feeds.items() if value.channel not in channels}
		metadata.items = [item for item in metadata.items if item.channel not in channels]

		self.set_status("Saving feed list...")
		task = app_data.create_save_feeds_task(self.loaded_feeds.values())
		task.signals.finished.connect(lambda result: self._io_complete([result]))
		self.executor.start(task)
	
	def set_status(self, message: str):
		self.status.setText(message)
	
	def enable_feed_actions(self, enabled=True):
		self.feed_menu.setEnabled(enabled)
		self.menu_refresh.setEnabled(enabled)
		self.refresh_action.setEnabled(enabled)
		self.menu_subscribe.setEnabled(enabled)
		self.toolbar_subscribe.setEnabled(enabled)
	
	def disable_feed_actions(self):
		self.enable_feed_actions(False)
	
	def exit_app(self):
		QCoreApplication.quit()

	@staticmethod
	def show_error(message: str):
		box = QMessageBox()
		box.setIcon(QMessageBox.Warning)
		box.setText(message)
		box.setWindowTitle("Error")
		box.exec_()
