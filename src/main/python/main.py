import json.decoder

from fbs_runtime.application_context.PyQt5 import ApplicationContext
from PyQt5.QtGui import QColor, QPalette

import logging
import sys
from typing import Dict

import config
from persist import app_data
import models


class MainApplicationContext(ApplicationContext):
    loaded_feeds: Dict[str, models.FeedDefinition]

    def run(self):
        from ui.app import MainApplication
        from ui import constants

        logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(asctime)s | %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")

        constants.setup(self)
        config.create_app_directories()

        # Load application data
        try:
            source = app_data.get_feeds()
            self.loaded_feeds = {feed.url: feed for feed in source}
        except json.decoder.JSONDecodeError:
            logging.error("Feed file is corrupted - resorting to using no loaded feeds")
            self.loaded_feeds = {}

        try:
            self.app_meta = app_data.get_app_meta() or models.AppMeta(items=[])
        except json.decoder.JSONDecodeError:
            logging.error("App metadata is corrupted - resorting to using empty metadata")
            self.app_meta = models.AppMeta(items=[])

        palette = QPalette()
        for key, value in constants.resources["palette"].items():
            palette.setColor(getattr(palette, key), QColor.fromRgb(*value))
        self.app.setPalette(palette)
        self.app.setStyleSheet(constants.resources["style/main"])

        window = MainApplication(self)
        window.setMinimumSize(600, 400)
        window.show()

        return self.app.exec_()
    
    def cleanup(self):
        if not app_data.save_app_meta(self.app_meta):
            logging.error("Failed to save application metadata - item states will not be persisted")


if __name__ == '__main__':
    app_ctxt = MainApplicationContext()
    exit_code = app_ctxt.run()
    app_ctxt.cleanup()
    sys.exit(exit_code)