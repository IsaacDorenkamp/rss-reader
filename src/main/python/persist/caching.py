from abc import ABC, abstractmethod
from collections import OrderedDict
import json
import os
import pathlib
import time

import typing
import datetime
from json import JSONEncoder
from typing import IO, TypeVar, Generic, Optional, Tuple

from config import FEED_CACHE

from reader.api import rss

T = TypeVar('T')


class AbstractCache(ABC, Generic[T]):
    @abstractmethod
    def set(self, key: str, value: T, ex: Optional[int] = None) -> bool:
        """
        :param key: The key of the cache entry to set.
        :param value: The value to assign to the cache entry.
        :param ex: The number of seconds before this entry should expire, or None if it should never expire.
        :return: Whether the set operation succeeded.
        """
        raise NotImplementedError()

    @abstractmethod
    def get(self, key: str) -> Optional[T]:
        """
        :param key: The key of the cache entry to get.
        :return: The value stored in the cache entry.
        """
        raise NotImplementedError()

    @abstractmethod
    def has(self, key: str) -> bool:
        """
        :param key: The key of the cache entry to check for.
        :return: Whether the key exists in this cache.
        """
        raise NotImplementedError()

    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        :param key: The key of the cache entry to delete.
        :return: Whether or not the key was deleted.
        """
        raise NotImplementedError()


V = TypeVar('V', bytes, str)


class FileCache(AbstractCache[T], Generic[T, V]):
    def __init__(self, location: pathlib.Path, extension: str = None, encoding=None):
        self.location = location
        self.extension = extension
        self.encoding = encoding

    @abstractmethod
    def write(self, value: Tuple[T, Optional[int]], destination: IO[V]):
        raise NotImplementedError()

    @abstractmethod
    def read(self, source: IO[V]) -> Tuple[T, Optional[int]]:
        raise NotImplementedError()

    @property
    def write_mode(self):
        return 'wb' if self.encoding is None else 'w'

    @property
    def read_mode(self):
        return 'rb' if self.encoding is None else 'r'

    def set(self, key: str, value: T, ex: int = None) -> bool:
        try:
            with open(os.path.join(self.location, self.with_extension(key)), mode=self.write_mode,
                      encoding=self.encoding) as fp:
                write_value = (value, int(time.time() + ex) if ex else None)
                self.write(write_value, fp)

            return True
        except IOError:
            return False

    def get(self, key: str) -> Optional[T]:
        try:
            with open(os.path.join(self.location, self.with_extension(key)), mode=self.read_mode,
                      encoding=self.encoding) as fp:
                value, expires = self.read(fp)
                if expires and time.time() > expires:
                    try:
                        self.delete(key)
                    except IOError:
                        # We can't really do anything about this, so just ignore
                        pass
                    return None
                else:
                    return value
        except FileNotFoundError:
            return None

    def has(self, key: str) -> bool:
        return os.path.isfile(self.entry_path(key))

    def delete(self, key: str) -> bool:
        try:
            entry_path = self.entry_path(key)
            if os.path.isfile(entry_path):
                os.remove(self.entry_path(key))
                return True
            else:
                return False
        except OSError:
            raise IOError("Failed to delete cache entry")

    def with_extension(self, key: str):
        if self.extension is None:
            return key
        else:
            return f'{key}.{self.extension}'

    def entry_path(self, key: str) -> pathlib.Path:
        return pathlib.Path(os.path.join(self.location, self.with_extension(key)))


class JSONDateEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.date):
            return obj.isoformat()
        else:
            return super().default(obj)


class ChannelFileCache(FileCache[rss.Channel, str]):
    def __init__(self, location=FEED_CACHE):
        super().__init__(location, 'json', encoding='utf-8')

    def write(self, value: Tuple[rss.Channel, Optional[int]], destination: IO[str]):
        json.dump([value[0].to_dict(), value[1]], destination, cls=JSONDateEncoder)

    def read(self, source: IO[str]) -> Tuple[rss.Channel, Optional[int]]:
        try:
            source_data, expires = json.load(source)
        except json.decoder.JSONDecodeError:
            return rss.Channel.Invalid, 0

        return rss.Channel.from_dict(source_data), expires


class LRUMemoryCache(AbstractCache[T]):
    maxsize: int
    cache: typing.OrderedDict[str, T]

    def __init__(self, maxsize: int = 16):
        self.maxsize = maxsize
        self.cache = OrderedDict()

    def set(self, key: str, value: T, ex: int = None) -> bool:
        self.cache[key] = (value, ex)
        self.cache.move_to_end(key, last=False)
        while len(self.cache) > self.maxsize:
            self.cache.popitem(last=True)

        return True

    def get(self, key: str) -> Optional[T]:
        if key in self.cache:
            value, expires = self.cache[key]

            if time.time() > expires:
                self.delete(key)
                return None
            else:
                self.cache.move_to_end(value, last=False)
                return value
        else:
            return None

    def has(self, key: str) -> bool:
        return key in self.cache

    def delete(self, key: str) -> bool:
        exists = key in self.cache.keys()
        self.cache.pop(key)
        return exists


class ChannelMultiCache(AbstractCache[rss.Channel]):
    memcache: LRUMemoryCache[rss.Channel]
    filecache: ChannelFileCache

    def __init__(self):
        self.memcache = LRUMemoryCache()
        self.filecache = ChannelFileCache()

    def get(self, key: str) -> Optional[rss.Channel]:
        mem = self.memcache.get(key)
        if mem is not None:
            return mem

        value = self.filecache.get(key)
        if value is not None:
            self.memcache.set(key, value)
            return value
        else:
            return None

    def set(self, key: str, value: rss.Channel, ex: int = None) -> bool:
        success = self.filecache.set(key, value, ex=ex)
        if not success:
            return False

        return self.memcache.set(key, value, ex=ex)

    def has(self, key: str) -> bool:
        # Check memcache for entry first as this is faster.
        return self.memcache.has(key) or self.filecache.has(key)

    def delete(self, key: str) -> bool:
        memcache_status = self.memcache.delete(key)
        filecache_status = self.filecache.delete(key)
        return memcache_status or filecache_status
