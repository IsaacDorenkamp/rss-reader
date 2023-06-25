from concurrency import tasks

from persist.caching import AbstractCache

from . import lockfile

import json
from typing import IO, TypeVar, Generic


T = TypeVar('T')


class SaveTask(tasks.Task):
    def __init__(self, path):
        super().__init__()
        self.path = path

    def execute(self):
        with open(self.path, 'w') as fp:
            lockfile.lock(fp)
            self.save(fp)

    # Conflict between ABCMeta and QObject metaclass
    # disables use of Python's abstract base classes
    def save(self, fp: IO[str]):
        raise NotImplementedError()
    
    def __str__(self):
        return f"save to \"{self.path}\""


class JSONSaveTask(SaveTask):
    def __init__(self, data, path):
        super().__init__(path)
        self.data = data

    def save(self, fp: IO[str]):
        json.dump(self.data, fp)
    
    def __str__(self):
        return "json " + super().__str__()


class CacheTask(tasks.Task, Generic[T]):
    def __init__(self, cache: AbstractCache[T], key: str, value: T):
        super().__init__()
        self.cache = cache
        self.key = key
        self.value = value

    def execute(self):
        self.cache.set(self.key, self.value)

    def __str__(self):
        return f"saving cache entry {self.key}"