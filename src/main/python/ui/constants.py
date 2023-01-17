from PyQt5.QtGui import QFont, QFontDatabase

global BASE_FONT
global TITLE_FONT

def setup():
	global BASE_FONT
	global TITLE_FONT

	BASE_FONT = QFont()
	BASE_FONT.setFamily(BASE_FONT.defaultFamily())

	TITLE_FONT = QFont(BASE_FONT.family())
	TITLE_FONT.setPointSize(18)