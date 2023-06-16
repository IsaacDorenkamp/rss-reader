import appdirs
import os
import tzlocal

APP_NAME = "Feedr"
APP_AUTHOR = "Isaac Dorenkamp"

APP_VERSION = "0.0.1"

global _user_data
global _user_cache

global USER_DATA
global USER_CACHE
global TIMEZONE

USER_DATA = appdirs.user_data_dir(APP_NAME, APP_AUTHOR, APP_VERSION)
USER_CACHE = appdirs.user_cache_dir(APP_NAME, APP_AUTHOR, APP_VERSION)
TIMEZONE = tzlocal.get_localzone()
DATETIME_FORMATS = [
    "%a, %d %b %Y %H:%M:%S %z",
    "%a, %d %b %Y %H:%M:%S %Z",
]

FEED_CACHE = os.path.join(USER_CACHE, 'feeds')

DEFAULT_TTL = 90 * 60  # 90 minutes


def create_app_directories():
    if not os.path.isdir(USER_DATA):
        os.makedirs(USER_DATA)

    if not os.path.isdir(USER_CACHE):
        os.makedirs(USER_CACHE)

    if not os.path.isdir(FEED_CACHE):
        os.makedirs(FEED_CACHE)
