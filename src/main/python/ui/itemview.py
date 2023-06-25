from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette
from PyQt5.QtWidgets import QFrame, QVBoxLayout, QLabel, QWidget, QTextEdit

from reader.api.rss import Item
from ui.constants import BASE_FONT, TITLE_FONT

from typing import Optional, Union

class ItemView(QFrame):
    _item: Optional[Item]

    def __init__(self, item: Union[Item, None] = None, parent: QWidget = None):
        super().__init__()
        self._setup_ui()
        self.set_item(item)
    
    def _setup_ui(self):
        vbox = QVBoxLayout(self)
        self.setLayout(vbox)

        self._title = QLabel()
        self._title.setFont(TITLE_FONT)

        self._author = QLabel()

        self._description = QTextEdit(self)
        self._description.setReadOnly(True)
        self._description.document().setDocumentMargin(0)

        palette = self._description.palette()
        palette.setColor(QPalette.Base, Qt.transparent)
        self._description.setPalette(palette)

        vbox.addWidget(self._title)
        vbox.addWidget(self._author)
        vbox.addWidget(self._description, stretch=1)
    
    def set_item(self, item: Union[Item, None]):
        self._description.clear()
        if item:
            self._title.setText(item.title)
            self._author.setText(item.author)
            self._description.insertHtml(item.description)
        else:
            self._title.setText("")
            self._author.setText("")
