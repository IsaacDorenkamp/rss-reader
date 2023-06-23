from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFontMetrics
from PyQt5.QtWidgets import QStyle

import typing

from reader.api.rss import Item
from .constants import TITLE_FONT, BASE_FONT


class FeedItemDelegate(QtWidgets.QStyledItemDelegate):
    ENABLED_TEXT_COLOR: QColor = QColor(0, 0, 0)
    DISABLED_TEXT_COLOR: QColor = QColor(128, 128, 128)

    _calculated: typing.Dict[int, typing.Tuple[QRect, int]]
    _parent: QtWidgets.QWidget
    _padding: QtCore.QMargins

    def __init__(self, parent: QtWidgets.QWidget, padding: QtCore.QMargins = QtCore.QMargins(7, 7, 7, 7)):
        super().__init__()
        self._calculated = {}
        self._parent = parent
        self._padding = padding
    
    def _render(self, item: Item, option: QtWidgets.QStyleOptionViewItem):
        key = id(item)
        if key not in self._calculated:
            # Note for future understanding: The width of option.rect varies between sizeHint() and paint().
            # It remains consistent between calls to the same function, however. It is certain that a call
            # to sizeHint() will certainly be made before a call to paint() for a given item. As a result,
            # what is rendered will be painted according to measurements calculated in the call to sizeHint().
            bounds = option.rect.marginsRemoved(self._padding)

            description = item.description.strip()
            
            title_height = QFontMetrics(TITLE_FONT, self._parent).height()
            desc_box = QFontMetrics(BASE_FONT, self._parent).boundingRect(bounds, Qt.TextWordWrap, description)
            bounds.setHeight(title_height + 10 + desc_box.height())
            self._calculated[key] = [bounds, title_height + 10]
        
        return self._calculated[key]

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        item: Item = index.data(role=Qt.DisplayRole)
        title: str = item.title
        description: str = item.description.strip()

        bounds, desc_offset = self._render(item, option)
        
        x, y = option.rect.x(), option.rect.y()
        item_box = bounds.adjusted(x, y, x, y)

        painter.setFont(TITLE_FONT)
        painter.drawText(item_box, Qt.TextSingleLine, title)

        item_box.adjust(0, desc_offset, 0, 0)
        painter.setFont(BASE_FONT)
        painter.drawText(item_box, Qt.TextWordWrap, description)


    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QSize:
        return self._render(index.data(role=Qt.DisplayRole), option)[0].marginsAdded(self._padding).size()
