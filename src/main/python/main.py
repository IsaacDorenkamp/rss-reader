import json.decoder

from fbs_runtime.application_context.PyQt5 import ApplicationContext
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

        # Load external resources
        style = constants.resources["style/main"] % constants.resources["style/colors"]
        try:
            source = app_data.get_feeds()
            self.loaded_feeds = {feed.url: feed for feed in source}
        except json.decoder.JSONDecodeError:
            self.loaded_feeds = {}

        window = MainApplication(self)
        window.setStyleSheet(style)
        window.resize(450, 300)
        window.setMinimumSize(450, 300)
        window.show()
        return self.app.exec_()


if __name__ == '__main__':
    app_ctxt = MainApplicationContext()
    exit_code = app_ctxt.run()
    sys.exit(exit_code)