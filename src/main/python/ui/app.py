from PyQt5.QtWidgets import QMainWindow, QAction, QListView, QHBoxLayout, QWidget, QMessageBox
import datetime
import functools
import logging
import os
import pytz
import time
import uuid
from typing import Dict, Union, Iterable, List

import config
from . import dialogs
from concurrency import tasks, fetcher
from ui.delegates import FeedItemDelegate
from ui.models import AggregateFeedModel
from persist import app_data, caching, concurrency
from reader.api.rss import Channel
from reader.api.xml import XMLEntityConstraintError
import main
import models


class MainApplication(QMainWindow):
	__ctx: main.MainApplicationContext
	tasks: tasks.TaskManager
	fetcher: fetcher.Fetcher
	channels: caching.ChannelMultiCache
	loaded_feeds: Dict[str, models.FeedDefinition]

	def __init__(self, ctx: main.MainApplicationContext, *args, **kw):
		super().__init__(*args, **kw)

		self.__ctx = ctx
		self.loaded_feeds = ctx.loaded_feeds.copy()
		self.tasks = tasks.BackgroundTasks()
		self.fetcher = fetcher.Fetcher(task_manager=self.tasks)
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
		self.content_pane.setLayout(top_layout)

		self.feed_aggregate = AggregateFeedModel(
			sort_by=lambda item: -(
				item.pub_date.timestamp() if item.pub_date else datetime.datetime.now(pytz.utc).timestamp()
			)
		)
		sidebar = QListView(self.content_pane)
		sidebar.setItemDelegate(FeedItemDelegate(sidebar))
		sidebar.setModel(self.feed_aggregate)

		top_layout.addWidget(sidebar)

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
			self.fetcher.fetch_all([feed_definition.url for feed_definition in to_fetch], functools.partial(
				self.on_fetch_batch, cached=results
			))
		elif results:
			self.on_fetch_batch({}, cached=results)

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
		self.refresh_action.triggered.connect(self.refresh)
		toolbar.addAction(self.refresh_action)

	def on_new_feed(self):
		dialog = dialogs.NewFeed()
		dialog.new_feed.connect(self.new_feed)
		dialog.show()
		dialog.exec_()

	def refresh(self):
		# TODO - what if fetch fails?
		self.refresh_action.setEnabled(False)
		self.fetcher.fetch_all(
			[feed_definition.url for feed_definition in self.loaded_feeds.values()],
			functools.partial(
				self.on_fetch_batch
			)
		)

	def new_feed(self, url):
		if self.feed_aggregate.has_url(url):
			# Ignore existing urls
			return

		# TODO - finish implementing this
		task = tasks.FetchTask(url)
		
		# task.success.connect(self.on_fetch_new)
		# task.failure.connect(self.on_fetch_fail)
		# self.tasks.start_task(task)

	def on_fetch_new(self, channel: Channel):
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
		self.tasks.start_task(save_task)

		self.channels.set(cache_key, channel, ex=(60 * 60 * 24 * 7))
		self.feed_aggregate.add(channel)

	def on_fetch_batch(self, results: Dict[str, Union[Channel, Exception]], **kw):
		cached = kw.get('cached', None)
		if cached:
			for channel in cached.values():
				logging.info("using cached feed - {}".format(channel.ref))
				self.feed_aggregate.add(channel)

		save_tasks = []
		for url, result in results.items():
			if isinstance(result, Exception):
				# TODO: GUI Error Display
				logging.error("{}: {}".format(result.__class__.__name__, str(result)))
			else:
				if result.ref in self.loaded_feeds:
					feed_def = self.loaded_feeds[result.ref]
					feed_def.update(result)
				else:
					feed_def = models.FeedDefinition.from_channel(result)
					self.loaded_feeds[feed_def.url] = feed_def

				if not feed_def.cache_key:
					feed_def.cache_key = str(uuid.uuid4())

				feed_def.last_retrieved = int(time.time())

				save_tasks.append(concurrency.CacheTask(self.channels, feed_def.cache_key, result))

				self.feed_aggregate.add(result)

		# TODO - trigger refresh re-enabled AFTER save task(s)
		self.refresh_action.setEnabled(True)

		save_tasks.append(
			concurrency.JSONSaveTask(
				models.FeedDefinition.to_multiple(self.loaded_feeds.values()), os.path.join(config.USER_DATA, 'feeds.json')
			)
		)

		self.tasks.start_all(save_tasks)

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
