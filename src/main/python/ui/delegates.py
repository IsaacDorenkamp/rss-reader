from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import QRect, QSize, Qt
from PyQt5.QtGui import QColor, QFontMetrics
from PyQt5.QtWidgets import QStyle

import typing

from reader.api.rss import Item
from .constants import MID_FONT, MID_FONT_BOLD, BASE_FONT


class FeedItemDelegate(QtWidgets.QStyledItemDelegate):
    ENABLED_TEXT_COLOR: QColor = QColor(0, 0, 0)
    DISABLED_TEXT_COLOR: QColor = QColor(128, 128, 128)

    _calculated: typing.Dict[int, typing.Tuple[QRect, int]]
    _parent: QtWidgets.QWidget
    _padding: QtCore.QMargins
    
    _title_metrics: QFontMetrics
    _unread_title_metrics: QFontMetrics
    _body_metrics: QFontMetrics

    def __init__(self, parent: QtWidgets.QWidget, padding: QtCore.QMargins = QtCore.QMargins(7, 7, 7, 7)):
        super().__init__()
        self._calculated = {}
        self._parent = parent
        self._padding = padding

        self._title_metrics = QFontMetrics(MID_FONT, self._parent)
        self._unread_title_metrics = QFontMetrics(MID_FONT_BOLD, self._parent)
        self._body_metrics = QFontMetrics(BASE_FONT, self._parent)
    
    def _render(self, item: Item, option: QtWidgets.QStyleOptionViewItem):
        bounds = option.rect.marginsRemoved(self._padding)

        description = item.plain_description
        
        title_metrics = self._unread_title_metrics if not item.read else self._title_metrics
        title_height = title_metrics.height()
        modified_title = title_metrics.elidedText(item.title, Qt.ElideRight, bounds.width())
        desc_box = self._body_metrics.boundingRect(bounds, Qt.TextWordWrap, description)
        desc_box.setHeight(min((self._body_metrics.height() * 3), desc_box.height()))
        bounds.setHeight(title_height + 10 + desc_box.height())
        return [bounds, title_height + 10, modified_title]

    def paint(self, painter: QtGui.QPainter, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex):
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())

        item: Item = index.data(role=Qt.DisplayRole)
        description: str = item.plain_description

        item_box, desc_offset, title = self._render(item, option)

        painter.setBrush(option.palette.text())
        painter.setFont(MID_FONT_BOLD if not item.read else MID_FONT)
        painter.drawText(item_box, Qt.TextSingleLine, title)

        item_box.adjust(0, desc_offset, 0, 0)
        painter.setFont(BASE_FONT)
        painter.drawText(item_box, Qt.TextWordWrap, description)

    def sizeHint(self, option: QtWidgets.QStyleOptionViewItem, index: QtCore.QModelIndex) -> QSize:
        return self._render(index.data(role=Qt.DisplayRole), option)[0].marginsAdded(self._padding).size()
