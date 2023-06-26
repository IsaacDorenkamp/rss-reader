from __future__ import annotations

from PyQt5.QtCore import QObject, QRunnable, QThreadPool, pyqtSignal

import functools
import logging
import requests
from typing import Generic, List, Optional, TypeVar

from reader.api import rss, xml


T = TypeVar('T')


class TaskResult(Generic[T]):
	data: Optional[T]
	error: Optional[BaseException]

	def __init__(self, data: Optional[T], error: Optional[BaseException]=None):
		self.data = data
		self.error = error


class TaskSignaller(QObject):
	finished = pyqtSignal(TaskResult)

	def __init__(self):
		super().__init__()


class Task(QRunnable, Generic[T]):
	signals: TaskSignaller

	def __init__(self):
		super().__init__()
		self.signals = TaskSignaller()

	def execute(self) -> T:
		raise NotImplementedError()
	
	def run(self):
		try:
			logging.info(f"[START] {str(self)}")
			result = TaskResult(self.execute())
			logging.info(f"[FINISH] {str(self)}")
		except BaseException as exc:
			logging.info(f"[FAIL] {str(self)}")
			result = TaskResult(None, exc)
		
		self.signals.finished.emit(result)


class FetchTask(Task[rss.Channel]):
	url: str

	def __init__(self, url):
		super().__init__()
		self.url = url

	def execute(self) -> rss.Channel:
		response = requests.get(self.url, headers={
			"Accept": "application/rss+xml"
		})
		response.raise_for_status()

		content = response.text
		channel = rss.parse_feed(content)
		channel.ref = self.url
		return channel
	
	def __str__(self):
		return f"fetch {self.url}"


class Batch(QObject, Generic[T]):
	_REGISTRY = []  # keep batches loaded in memory while running

	complete = pyqtSignal(list)
	results: List[TaskResult]

	_tasks: List[Task[T]]

	def __init__(self, tasks: List[Task[T]]):
		super().__init__()
		self._tasks = tasks
		self.results = [None for _ in tasks]
	
	def start(self, pool: QThreadPool):
		if not self._tasks:
			self.complete.emit([])
			return

		Batch._REGISTRY.append(self)
		for idx, task in enumerate(self._tasks):
			task.signals.finished.connect(functools.partial(self._complete, idx))
			pool.start(task)
	
	def _complete(self, index: int, result: TaskResult):
		self.results[index] = result
		if all([item is not None for item in self.results]):
			self.complete.emit(self.results)
			Batch._REGISTRY.remove(self)
