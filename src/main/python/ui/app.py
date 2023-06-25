from PyQt5.QtWidgets import QMainWindow, QAction, QListView, QHBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import QThreadPool, QItemSelection, Qt

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
from reader.api.xml import XMLEntityConstraintError
from ui.delegates import FeedItemDelegate
from ui.models import AggregateFeedModel

from . import dialogs
from .itemview import ItemView


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
		version = self.__ctx.build_settings['version']
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

		sidebar = QListView(self.content_pane)
		sidebar.setFixedWidth(300)
		sidebar.setItemDelegate(FeedItemDelegate(sidebar))
		sidebar.setModel(self.feed_aggregate)
		sidebar.selectionModel().selectionChanged.connect(self._change_item)

		self._content = ItemView(parent=self)
		self._content.setContentsMargins(5, 5, 5, 5)

		top_layout.addWidget(sidebar)
		top_layout.addWidget(self._content)

	def _setup(self):
		self.try_fetch(self.loaded_feeds.values())

	def try_fetch(self, feed_definitions: Iterable[models.FeedDefinition]):
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
						results[feed_definition.url] = cached
					else:
						if now.timestamp() > feed_definition.last_retrieved + ttl:
							to_fetch.append(feed_definition)
						else:
							results[feed_definition.url] = cached

		# fetch non-cached entries
		if to_fetch:
			batch = tasks.Batch([tasks.FetchTask(feed_definition.url) for feed_definition in to_fetch])
			batch.complete.connect(functools.partial(self.on_fetch_batch, cached=results))
			batch.start(self.executor)
		elif results:
			self.on_fetch_batch([], cached=results)

	def _setup_menubar(self):
		menu_bar = self.menuBar()

		new_feed = QAction("New Feed", self)
		new_feed.setShortcut("Ctrl+N")
		new_feed.triggered.connect(self.on_new_feed)

		feeds = menu_bar.addMenu("&Feeds")
		feeds.addAction(new_feed)
	
	def _setup_toolbar(self):
		toolbar = self.addToolBar("Feeds")

		self.refresh_action = QAction("&Refresh", self)
		self.refresh_action.triggered.connect(self.refresh_feeds)
		toolbar.addAction(self.refresh_action)
	
	def _change_item(self, selection: QItemSelection):
		indexes = selection.indexes()
		if indexes:
			index = indexes[0]
			self._content.set_item(index.data(role=Qt.DisplayRole))

	def on_new_feed(self):
		dialog = dialogs.NewFeed()
		dialog.new_feed.connect(self.new_feed)
		dialog.show()
		dialog.exec_()

	def refresh_feeds(self):
		self.refresh_action.setEnabled(False)

		batch = tasks.Batch([tasks.FetchTask(feed_definition.url) for feed_definition in self.loaded_feeds.values()])
		batch.complete.connect(self.on_fetch_batch)
		batch.start(self.executor)

	def new_feed(self, url):
		task = tasks.FetchTask(url)
		task.signals.finished.connect(self.on_fetch_new)
		self.executor.start(task)

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

		feed_definition = self.loaded_feeds.get(channel.ref)
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
			self.loaded_feeds[channel.ref] = feed_definition

		save_task = app_data.create_save_feeds_task(self.loaded_feeds.values())
		self.executor.start(save_task)

		self.channels.set(cache_key, channel, ex=(60 * 60 * 24 * 7))
		self.feed_aggregate.add(channel)

	def on_fetch_batch(self, results: List[tasks.TaskResult[Channel]], **kw):
		cached = kw.get('cached', None)
		if cached:
			for channel in cached.values():
				logging.info("using cached feed - {}".format(channel.ref))
				self.feed_aggregate.add(channel)

		io_tasks = []
		for result in results:
			if result.error:
				# TODO: GUI Error Display
				logging.error("{}: {}".format(result.error.__class__.__name__, str(result.error)))
			else:
				result = result.data
				if result.ref in self.loaded_feeds:
					feed_def = self.loaded_feeds[result.ref]
					feed_def.update(result)
				else:
					feed_def = models.FeedDefinition.from_channel(result)
					self.loaded_feeds[feed_def.url] = feed_def

				feed_def.last_retrieved = int(time.time())
				if not feed_def.cache_key:
					feed_def.cache_key = str(uuid.uuid4())

				io_tasks.append(iotasks.CacheTask(self.channels, feed_def.cache_key, result))

				self.feed_aggregate.add(result)

		io_tasks.append(
			iotasks.JSONSaveTask(
				models.FeedDefinition.to_multiple(self.loaded_feeds.values()), os.path.join(config.USER_DATA, 'feeds.json')
			)
		)

		io_batch = tasks.Batch(io_tasks)
		io_batch.complete.connect(self._io_complete)
		io_batch.start(self.executor)
	
	def _io_complete(self, results: tasks.TaskResult):
		for result in results:
			if result.error:
				logging.error("{}: {}".format(result.error.__class__.__name__, str(result.error)))
		
		self.refresh_action.setEnabled(True)

	@classmethod
	def on_fetch_fail(cls, exc: Exception):
		# TODO: Implement error reporting
		logging.error("{}: {}".format(exc.__class__.__name__, str(exc)))

		if isinstance(exc, XMLEntityConstraintError):
			message = "The received RSS feed was invalid."
		else:
			message = "Couldn't retrieve the desired feed."

		cls.show_error(message)

	@staticmethod
	def show_error(message: str):
		box = QMessageBox()
		box.setIcon(QMessageBox.Warning)
		box.setText(message)
		box.setWindowTitle("Error")
		box.exec_()
