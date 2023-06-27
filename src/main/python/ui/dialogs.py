from fbs_runtime import PUBLIC_SETTINGS
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, Qt, QVariant

import typing

from models import FeedDefinition

from . import constants

class NewFeed(QDialog):
	new_feed = pyqtSignal(str)

	def __init__(self):
		super().__init__()
		self._setup_ui()

	def _setup_ui(self):
		self.setWindowTitle("New Feed")

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		main = QWidget()
		hbox = QHBoxLayout()
		main.setLayout(hbox)

		label = QLabel("Feed URL:", main)
		self.url_input = QLineEdit(main)
		hbox.addWidget(label)
		hbox.addWidget(self.url_input)

		btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		btns.accepted.connect(self.on_create)
		btns.rejected.connect(self.reject)

		vbox.addWidget(main)
		vbox.addWidget(btns)

	def on_create(self):
		self.new_feed.emit(self.url_input.text())
		self.accept()


class AboutDialog(QDialog):
	def __init__(self):
		super().__init__()
		self._setup_ui()

	def _setup_ui(self):
		self.setWindowTitle(f"About {PUBLIC_SETTINGS['app_name']} v{PUBLIC_SETTINGS['version']}")

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		desc = QLabel(constants.resources["about"], parent=self)
		btns = QDialogButtonBox(QDialogButtonBox.Ok)
		btns.accepted.connect(self.accept)

		vbox.addWidget(desc)
		vbox.addWidget(btns)


class FeedItem(QListWidgetItem):
	feed: FeedDefinition

	def __init__(self, feed: FeedDefinition):
		super().__init__()
		self.feed = feed
	
	def data(self, role: Qt.ItemDataRole) -> object:
		if role == Qt.DisplayRole:
			return self.feed.nickname
		elif role == Qt.UserRole:
			return self.feed
		else:
			return QVariant()


class ManageSubscriptions(QDialog):
	_feeds: typing.List[FeedDefinition]
	_model: typing.List[FeedItem]
	_selection: typing.Optional[FeedDefinition] = None

	removed: typing.List[str]  # identified by channel <link>

	def __init__(self, feeds: typing.List[FeedDefinition]):
		super().__init__()
		self._feeds = feeds
		self.removed = []
		self._setup_ui()
	
	def _setup_ui(self):
		self.setWindowTitle("Manage Subscriptions")

		vbox = QVBoxLayout(spacing=0)
		vbox.setContentsMargins(0, 0, 0, 0)
		self.setLayout(vbox)

		self._subscriptions = QListWidget(self)
		self._model = []
		for feed in self._feeds:
			item = FeedItem(feed)
			self._model.append(item)
			self._subscriptions.addItem(item)

		self._subscriptions.itemSelectionChanged.connect(self._selection_changed)
		
		self.unsubscribe = QPushButton(text="Unsubscribe", parent=self)
		self.unsubscribe.clicked.connect(self.remove_feed)
		self.unsubscribe.setEnabled(False)

		controls = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
		controls.button(QDialogButtonBox.Ok).setText("Confirm")
		controls.setContentsMargins(10, 10, 10, 10)
		controls.rejected.connect(self.reject)
		controls.accepted.connect(self.accept)

		vbox.addWidget(self._subscriptions)
		vbox.addWidget(self.unsubscribe)
		vbox.addWidget(controls)
	
	def _selection_changed(self):
		items = self._subscriptions.selectedItems()
		if not items:
			self._selection = None
			self.unsubscribe.setEnabled(False)
		else:
			self._selection = items[0].data(role=Qt.UserRole)
			self.unsubscribe.setEnabled(True)
	
	def remove_feed(self):
		if not self._selection:
			return

		to_remove = -1
		for idx, item in enumerate(self._model):
			feed = item.data(role=Qt.UserRole)
			if feed.channel == self._selection.channel:
				to_remove = idx
				break
		
		if to_remove >= 0:
			self._model.pop(to_remove)
			item = self._subscriptions.takeItem(to_remove)
			if item:
				self.removed.append(item.data(role=Qt.UserRole).channel)
