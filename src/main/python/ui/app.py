from PyQt5.QtWidgets import QMainWindow, QAction, QMenu, QListView, QHBoxLayout, QWidget, QAbstractItemView, QScrollArea
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt

from . import dialogs, feedview
import tasks
import models

class MainApplication(QMainWindow):
	def __init__(self, ctx, *args, **kw):
		super().__init__(*args, **kw)

		self.__ctx = ctx
		self.tasks = tasks.TaskManager()
		self._setup_ui()

	def _setup_ui(self):
		version = self.__ctx.build_settings['version']
		self.setWindowTitle(f"RSS Reader v{version}")

		self._setup_menubar()

		self.content_pane = QWidget()
		self.setCentralWidget(self.content_pane)

		top_layout = QHBoxLayout()
		self.content_pane.setLayout(top_layout)

		self.feeds_view = QListView()
		self.feeds = models.FeedModel()
		self.feeds_view.setModel(self.feeds)
		self.feeds_view.setSelectionMode(QAbstractItemView.SingleSelection)
		self.feeds_view.selectionModel().selectionChanged.connect(self.on_feed_selected)

		self.items_scroller = QScrollArea(self.content_pane)
		self.items_view = feedview.FeedView(self.items_scroller)
		self.items_scroller.setWidget(self.items_view)
		self.items_scroller.setWidgetResizable(True)

		top_layout.addWidget(self.feeds_view, stretch=1)
		top_layout.addWidget(self.items_scroller, stretch=2)

	def _setup_menubar(self):
		menu_bar = self.menuBar()

		new_feed = QAction("New Feed", self)
		new_feed.triggered.connect(self.on_new_feed)

		feeds = menu_bar.addMenu("&Feeds")
		feeds.addAction(new_feed)

	def on_new_feed(self):
		dialog = dialogs.NewFeed()
		dialog.new_feed.connect(self.new_feed)
		dialog.show()
		dialog.exec_()

	def new_feed(self, url):
		task = tasks.FetchFeed(url)
		task.success.connect(self.on_fetch)
		task.failure.connect(self.on_fetch_fail)
		self.tasks.start_task(task)

	def on_fetch(self, channel):
		self.feeds.append(channel)

	def on_fetch_fail(self, exc):
		# TODO: Implement dialog or something
		print(exc)

	def on_feed_selected(self, selected, deselected):
		items = selected.indexes()
		if len(items) > 0:
			index = items[0]
			feed = index.data(Qt.UserRole)
			self.items_view.set_channel(feed)