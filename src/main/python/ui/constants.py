from fbs_runtime.application_context.PyQt5 import ApplicationContext
from fbs_runtime import PUBLIC_SETTINGS
from PyQt5.QtGui import QFont, QIcon

import json
import sys
import typing

global BASE_FONT
global MID_FONT
global MID_FONT_BOLD
global TITLE_FONT

BASE_FONT = QFont()
MID_FONT = QFont()
MID_FONT_BOLD = QFont()
TITLE_FONT = QFont()


def fatal(exc, status=1):
	print("FATAL ERROR: %s" % str(exc))
	sys.exit(status)


def _create_fonts():
	global BASE_FONT
	global MID_FONT
	global TITLE_FONT

	BASE_FONT.setFamily(BASE_FONT.defaultFamily())

	MID_FONT.setFamily(BASE_FONT.family())
	MID_FONT.setPointSize(14)

	MID_FONT_BOLD.setFamily(BASE_FONT.family())
	MID_FONT_BOLD.setPointSize(14)
	MID_FONT_BOLD.setBold(True)

	TITLE_FONT.setFamily(BASE_FONT.family())
	TITLE_FONT.setPointSize(18)


def format_public_settings(fp: typing.TextIO):
	text = fp.read()
	return text % PUBLIC_SETTINGS


global resources
resources = {
	"style/main": {
		"file": "main.qss",
	},
	"palette": {
		"file": "palette.json",
		"load": json.load
	},
	"about": {
		"file": "about.txt",
		"load": format_public_settings
	},
	"icons/plus": {
		"file": "icons/png/13.png",
		"open": False,
		"load": QIcon
	},
	"icons/refresh": {
		"file": "icons/png/42.png",
		"open": False,
		"load": QIcon
	}
}


def _read_file(fp):
	return fp.read()


def _load_resources(context: ApplicationContext):
	for key, resource_definition in resources.items():
		filename = context.get_resource(resource_definition["file"])
		loader = resource_definition.get("load", _read_file)
		try:
			should_open = resource_definition.get("open", True)
			if should_open:
				with open(filename, 'r', encoding='utf-8') as fp:
					resources[key] = loader(fp)
			else:
				resources[key] = loader(filename)
		except (IOError, json.decoder.JSONDecodeError) as exc:
			fatal(exc)


def setup(context):
	_create_fonts()
	_load_resources(context)
