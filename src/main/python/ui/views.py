from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFontMetrics, QPalette, QResizeEvent
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QTextEdit

from reader.api.rss import Item
from ui.constants import TITLE_FONT

from typing import Optional, Union

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

        self._description = QTextEdit(self)
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
