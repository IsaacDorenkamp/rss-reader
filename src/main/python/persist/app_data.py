import config
import models
from .tasks import JSONSaveTask

import os
from typing import Tuple, Iterable, Union

FEED_DEFINITIONS = os.path.join(config.USER_DATA, 'feeds.json')
APPLICATION_META = os.path.join(config.USER_DATA, 'meta.json')


def get_feeds() -> Union[Tuple[models.FeedDefinition], Tuple[()]]:
    try:
        with open(FEED_DEFINITIONS, 'r') as fp:
            return models.FeedDefinition.load_multiple(fp)
    except FileNotFoundError:
        return ()


def get_app_meta() -> Union[models.AppMeta, None]:
    try:
        with open(APPLICATION_META, 'r') as fp:
            return models.AppMeta.load(fp)
    except FileNotFoundError:
        return None
    

def save_app_meta(meta: models.AppMeta) -> bool:
    try:
        with open(APPLICATION_META, 'w') as fp:
            models.AppMeta.save(meta, fp)

        return True
    except IOError:
        return False


def create_save_feeds_task(feeds: Iterable[models.FeedDefinition]) -> JSONSaveTask:
    output = models.JSONModel.to_multiple(feeds)
    return JSONSaveTask(output, FEED_DEFINITIONS)