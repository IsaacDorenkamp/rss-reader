import typing

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QModelIndex

import bisect

from typing import Optional, Union, List, Iterable, Callable, Tuple, Generator, TypeVar
from reader.api.rss import Channel, Item
from util.comparable import Comparable, keyed


class AggregateFeedModel(QtCore.QAbstractListModel):
	"""
	A QT model that tracks multiple channels and adds individual items into a single list in order. Able to handle
	the adding of new channels that contain items that must be inserted earlier in the sequence.
	"""

	DEFAULT_BATCH_SIZE = 100

	fetch_batch_size: int
	"""
	The number of items that should be fetched with each call to fetchMore(qIndex).
	"""

	_items: List[Tuple[Item, str]]
	_sorter: Callable[[Item], Comparable]

	def __init__(self, sort_by: Callable[[Item], Comparable], feeds: Optional[Iterable[Channel]] = None):
		super().__init__()
		self._sorter = sort_by
		if feeds:
			self._items = sorted(
				sum([
					[(item, channel.ref) for item in channel.items] for channel in feeds
				], []), key=lambda item: self._sorter(item[0])
			)
		else:
			self._items = []

	def _add_one(self, item: Item, url: str):
		# TODO: Is there a way to optimize non-continguous row insertions?
		end_idx = len(self._items)
		self.beginInsertRows(QModelIndex(), end_idx, end_idx)
		self._items.append((item, url))

	def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Union[str, Item]:
		if role == Qt.DisplayRole:
			row = index.row()
			item = self._items[row][0]
			return item.title

	def add(self, value: Channel):
		for item in value.items:
			index = bisect.bisect_left(keyed(self._items, key=lambda item_: self._sorter(item_[0])), self._sorter(item))
			self.beginInsertRows(QModelIndex(), index, index)
			self._items.insert(index, (item, value.ref))
			self.endInsertRows()

	def update(self, value: Channel):
		for i in range(len(self._items) - 1, -1, -1):
			item = self._items[i]
			should_remove = item[1] == value.ref
			if should_remove:
				self.beginRemoveRows(QModelIndex(), i, i)
				self._items.pop(i)
				self.endRemoveRows()

		self.add(value)

	def has_url(self, url: str) -> bool:
		return any(map(lambda item: item[1] == url, self._items))

	def rowCount(self, parent: QModelIndex = QModelIndex()):
		total = len(self._items)
		if parent.isValid():
			total - (parent.row() + 1)
		else:
			return total

	@property
	def items(self) -> Generator[Item, None, None]:
		for item, _ in self._items:
			yield item
