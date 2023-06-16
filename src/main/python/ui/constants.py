from PyQt5.QtGui import QFont, QFontDatabase
from fbs_runtime.application_context.PyQt5 import ApplicationContext

import json
import sys

global BASE_FONT
global MID_FONT
global TITLE_FONT


def fatal(exc, status=1):
	print("FATAL ERROR: %s" % str(exc))
	sys.exit(status)


def _create_fonts():
	global BASE_FONT
	global MID_FONT
	global TITLE_FONT

	BASE_FONT = QFont()
	BASE_FONT.setFamily(BASE_FONT.defaultFamily())

	MID_FONT = QFont(BASE_FONT.family())
	MID_FONT.setPointSize(14)

	TITLE_FONT = QFont(BASE_FONT.family())
	TITLE_FONT.setPointSize(18)


global resources
resources = {
	"style/main": {
		"file": "main.qss",
	},
	"style/colors": {
		"file": "palette.json",
		"load": json.load
	}
}


def _read_file(fp):
	return fp.read()


def _load_resources(context: ApplicationContext):
	for key, resource_definition in resources.items():
		filename = context.get_resource(resource_definition["file"])
		loader = resource_definition.get("load", _read_file)
		try:
			with open(filename, 'r', encoding='utf-8') as fp:
				resources[key] = loader(fp)
		except (IOError, json.decoder.JSONDecodeError) as exc:
			fatal(exc)


def setup(context):
	_create_fonts()
	_load_resources(context)
