from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel

from reader.api import rss
from ui import constants

class ItemView(QWidget):
	def __init__(self, item, parent=None):
		super().__init__(parent=parent)

		assert isinstance(item, rss.Item), TypeError("item must be an instance of reader.api.rss.Item")
		self._item = item

		self._setup_ui()

	def _setup_ui(self):
		self.setStyleSheet("border: 1px solid black;")

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		item = self._item
		if item.title:
			print(item.title)
			title = QLabel(item.title, self)
			title.setFont(constants.TITLE_FONT)
			vbox.addWidget(title)

	@property
	def item(self):
		return self._item

class FeedView(QWidget):
	def __init__(self, parent=None, channel=None):
		super().__init__(parent=parent)

		self._setup_ui()
		self.set_channel(channel)

	def _setup_ui(self):
		self.layout = QVBoxLayout()
		self.setLayout(self.layout)

	def set_channel(self, channel):
		self.__channel = channel

		# Remove all children
		for idx in reversed(range(self.layout.count())):
			self.layout.itemAt(idx).widget().setParent(None)

		if channel is None:
			return

		for item in channel.items:
			view = ItemView(item, parent=self)
			self.layout.addWidget(view)