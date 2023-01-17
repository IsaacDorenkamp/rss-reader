from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QWidget, QLabel, QLineEdit, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt5.QtCore import pyqtSignal

class NewFeed(QDialog):
	new_feed = pyqtSignal(str)

	def __init__(self):
		super().__init__()
		self.__setup_ui()

	def __setup_ui(self):
		self.setWindowTitle("New Feed")

		vbox = QVBoxLayout()
		self.setLayout(vbox)

		main = QWidget()
		hbox = QHBoxLayout()
		main.setLayout(hbox)

		label = QLabel("Feed URL:", main)
		self.url_input = QLineEdit(main)
		hbox.addWidget(label)
		hbox.addWidget(self.url_input)

		btns = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
		btns.accepted.connect(self.on_create)
		btns.rejected.connect(self.reject)

		vbox.addWidget(main)
		vbox.addWidget(btns)

	def on_create(self):
		self.new_feed.emit(self.url_input.text())
		self.accept()