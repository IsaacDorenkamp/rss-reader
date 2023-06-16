from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QListWidget, QListWidgetItem
from PyQt5.QtCore import Qt, QSize

from reader.api import rss
from ui import constants

from typing import Optional, List, TypeVar


Widget = TypeVar('Widget', bound=QWidget)


class ItemView(QFrame):
	def __init__(self, item, parent=None):
		super().__init__(parent=parent)

		assert isinstance(item, rss.Item), TypeError("item must be an instance of reader.api.rss.Item")
		self._item = item

		self._setup_ui()

	def _setup_ui(self):
		vbox = QVBoxLayout()
		self.setLayout(vbox)
		self.setFixedHeight(300)

		item = self._item
		if item.title:
			self.title = title = QLabel(item.title, self)
			title.setTextInteractionFlags(Qt.TextSelectableByMouse)
			title.setFont(constants.TITLE_FONT)
			vbox.addWidget(title)

		if item.description:
			self.desc = desc = QLabel(item.description, self)
			desc.setTextInteractionFlags(Qt.TextSelectableByMouse)
			desc.setWordWrap(True)
			desc.setFont(constants.BASE_FONT)
			vbox.addWidget(desc)

	@property
	def item(self):
		return self._item

	@item.setter
	def item(self, item):
		self._item = item
		self.title.setText(item.title)
		self.desc.setText(item.description)


class FeedView(QWidget):
	def __init__(self, parent=None):
		super().__init__(parent=parent)
		self._setup_ui()

	def _setup_ui(self):
		self.layout = QVBoxLayout()
		self.setLayout(self.layout)

	def clear(self):
		for idx in reversed(range(self.layout.count())):
			self.layout.itemAt(idx).widget().setParent(None)

	def add_item(self, item):
		view = ItemView(item, parent=self)
		view.setFrameStyle(QFrame.Panel | QFrame.Plain)
		self.layout.addWidget(view)


class ChannelListWidget(QListWidget):
	_items: List[ItemView]

	def __init__(self, parent: Optional[Widget] = None):
		super(ChannelListWidget, self).__init__(parent=parent)
		self._items = []

	def set_channel(self, channel: rss.Channel):
		result_len = len(channel.items)
		cur_len = len(self._items)
		end_index = min(result_len, cur_len)
		for index in range(end_index):
			item_view = self._items[index]
			item_view.item = channel.items[index]

		to_add = max(0, result_len - cur_len)
		for index in range(to_add):
			item = QListWidgetItem(self)
			self.addItem(item)
			item.setSizeHint(QSize(self.width(), 300))
			item_view = ItemView(channel.items[index + cur_len])
			self._items.append(item_view)
			self.setItemWidget(item, item_view)

		to_remove = max(0, cur_len - result_len)
		for index in range(result_len + to_remove, cur_len):
			self.removeItemWidget(self.item(index))

		del self._items[result_len + to_remove:]


