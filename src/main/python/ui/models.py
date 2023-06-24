from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QModelIndex

import bisect

from typing import Optional, Union, List, Iterable, Callable, Generator
from reader.api.rss import Channel, Item
from util.comparable import Comparable, keyed


class AggregateFeedModel(QtCore.QAbstractListModel):
	"""
	A QT model that tracks multiple channels and adds individual items into a single list in order. Able to handle
	the adding of new channels that contain items that must be inserted earlier in the sequence.
	"""

	DEFAULT_BATCH_SIZE = 10

	fetch_batch_size: int
	"""
	The number of items that should be fetched with each call to fetchMore(qIndex).
	"""

	_items: List[Item]
	_loaded: int
	_sorter: Callable[[Item], Comparable]

	def __init__(self, sort_by: Callable[[Item], Comparable], feeds: Optional[Iterable[Channel]] = None, fetch_batch_size = DEFAULT_BATCH_SIZE):
		super().__init__()
		self._sorter = sort_by
		self.fetch_batch_size = fetch_batch_size
		self._loaded = 0
		if feeds:
			self._items = sorted(
				sum([
					list(channel.items) for channel in feeds
				], []), key=lambda item: self._sorter(item)
			)
		else:
			self._items = []

	def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Union[Item, QtCore.QSize, None]:
		if role == Qt.DisplayRole:
			return self._items[index.row()]

	def add(self, value: Channel):
		for item in value.items:
			if item in self._items:
				continue

			index = bisect.bisect_left(keyed(self._items, key=lambda item_: self._sorter(item_)), self._sorter(item))

			should_insert = index < self._loaded
			if should_insert:
				self._loaded += 1
				self.beginInsertRows(QModelIndex(), index, index)

			self._items.insert(index, item)

			if should_insert:
				self.endInsertRows()

	def has_url(self, url: str) -> bool:
		return any(map(lambda item: item._parent.link == url or item._parent.ref == url, self._items))

	def rowCount(self, parent: QModelIndex = QModelIndex()):
		total = self._loaded
		if parent.isValid():
			total - (parent.row() + 1)
		else:
			return total
	
	def canFetchMore(self, parent: QModelIndex = QModelIndex()) -> bool:
		if parent.isValid():
			return False
	
		return self._loaded < len(self._items)
	
	def fetchMore(self, parent: QModelIndex = QModelIndex()):
		if parent.isValid():
			return
		
		unloaded = len(self._items) - self._loaded
		to_fetch = min(unloaded, self.fetch_batch_size)

		self.beginInsertRows(parent, self._loaded, self._loaded + to_fetch - 1)
		self._loaded += to_fetch
		self.endInsertRows()

	@property
	def items(self) -> Generator[Item, None, None]:
		yield from self._items
