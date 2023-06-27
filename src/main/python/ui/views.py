from PyQt5 import QtGui
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices, QMouseEvent, QPalette, QResizeEvent
from PyQt5.QtWidgets import QApplication, QFrame, QVBoxLayout, QLabel, QWidget, QTextEdit

from reader.api.rss import Item
from ui.constants import TITLE_FONT

from typing import Optional, Union

class DynamicItemContent(QTextEdit):
    _use_anchor: bool = False
    _anchor: Optional[str] = None

    def __init__(self, *args, **kw):
        super().__init__(*args, **kw)
        self.zoomIn(2)

    def mousePressEvent(self, e: QMouseEvent):
        super().mousePressEvent(e)
        if e.button() == Qt.MouseButton.LeftButton:
            self._use_anchor = True
    
    def mouseMoveEvent(self, e: QMouseEvent):
        super().mouseMoveEvent(e)
        new_anchor = self.anchorAt(e.pos())
        if new_anchor != self._anchor:
            if new_anchor:
                QApplication.setOverrideCursor(Qt.PointingHandCursor)
            else:
                QApplication.restoreOverrideCursor()
        
        self._anchor = new_anchor
    
    def mouseReleaseEvent(self, e: QMouseEvent):
        super().mouseReleaseEvent(e)
        if e.button() == Qt.MouseButton.LeftButton:
            if self._anchor and self._use_anchor:
                QDesktopServices.openUrl(QUrl(self._anchor))
            
            QApplication.restoreOverrideCursor()
            self._anchor = None
            self._use_anchor = False

class ItemView(QFrame):
    _item: Optional[Item]

    def __init__(self, item: Union[Item, None] = None, parent: QWidget = None):
        super().__init__()
        self._setup_ui()
        self.set_item(item)

    def resizeEvent(self, event: QResizeEvent):
        if self._item:
            elided = self._title.fontMetrics().elidedText(
                self._item.title,
                Qt.ElideRight,
                self._title.contentsRect().width()
            )
            self._title.setText(elided)
    
    def _setup_ui(self):
        vbox = QVBoxLayout(self, spacing=0)
        vbox.setContentsMargins(0, 0, 0, 0)
        self.setLayout(vbox)

        self._title = QLabel()
        self._title.setContentsMargins(10, 10, 10, 10)
        self._title.setFont(TITLE_FONT)

        self._author = QLabel() 
        self._author.setContentsMargins(10, 0, 10, 10)

        self._description = DynamicItemContent(self)
        self._description.setReadOnly(True)
        self._description.setFrameStyle(QFrame.NoFrame)
        self._description.document().setDocumentMargin(10)

        palette = self._description.palette()
        palette.setColor(QPalette.Base, Qt.transparent)
        self._description.setPalette(palette)

        vbox.addWidget(self._title)
        vbox.addWidget(self._author)
        vbox.addWidget(self._description, stretch=1)
    
    def set_item(self, item: Union[Item, None]):
        self._item = item
        if item:
            self._title.setText(
                self._title.fontMetrics().elidedText(
                    item.title,
                    Qt.ElideRight,
                    self._title.contentsRect().width()
                )
            )
            self._title.setToolTip(item.title)

            if item.author:
                font = self._author.font()
                font.setItalic(False)
                self._author.setFont(font)
                self._author.setText("by " + item.author)
            else:
                font = self._author.font()
                font.setItalic(True)
                self._author.setFont(font)
                self._author.setText("No Listed Author")

            self._description.setHtml(item.description)
        else:
            self._title.setText("")
            self._title.setToolTip("")
            self._author.setText("")
            self._description.clear()
