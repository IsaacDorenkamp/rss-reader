from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtWidgets import QAbstractItemView

from reader.api import rss

class FeedModel(QtCore.QAbstractListModel):
	def __init__(self, feeds=None):
		super().__init__()
		self.feeds = feeds or []

	def data(self, index, role):
		if role == Qt.DisplayRole:
			row = index.row()
			feed = self.feeds[row]
			return feed.title
		elif role == Qt.UserRole:
			return self.feeds[index.row()]

	def setData(self, index, value, role=Qt.UserRole):
		if role == Qt.UserRole:
			row = index.row()
			self.feeds[row] = value
			self.dataChanged.emit(index, index)
			return True
		else:
			return False

	def append(self, value):
		idx = len(self.feeds)
		self.beginInsertRows(QModelIndex(), idx, idx)
		self.feeds.append(value)
		self.endInsertRows()

	def rowCount(self, parent):
		total = len(self.feeds)
		if parent.isValid():
			total - (parent.row() + 1)
		else:
			return total