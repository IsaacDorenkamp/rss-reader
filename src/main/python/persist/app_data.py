import config
import models
from .concurrency import JSONSaveTask

import os
from typing import Tuple, Iterable, Union

FEED_DEFINITIONS = os.path.join(config.USER_DATA, 'feeds.json')


def get_feeds() -> Union[Tuple[models.FeedDefinition], Tuple[()]]:
    try:
        with open(FEED_DEFINITIONS, 'r') as fp:
            return models.FeedDefinition.load_multiple(fp)
    except FileNotFoundError:
        return ()


def create_save_feeds_task(feeds: Iterable[models.FeedDefinition]) -> JSONSaveTask:
    output = models.JSONModel.to_multiple(feeds)
    return JSONSaveTask(output, FEED_DEFINITIONS)