from __future__ import annotations

from PyQt5.QtCore import QObject, QThread, pyqtSignal
import requests
import functools
from typing import Generic, Tuple, TypeVar, Union

from reader.api import rss, xml


T = TypeVar('T')


class Task(QObject, Generic[T]):
	finished = pyqtSignal()

	result: Tuple[bool, Union[T, BaseException]] = None  # tuple is structured to be (is_error, result_or_exception)

	def __init__(self):
		super().__init__()

	def run(self) -> T:
		raise NotImplementedError()
	
	def handle_error(self, error: BaseException):
		raise NotImplementedError()
	
	def handle_result(self, result: T):
		raise NotImplementedError()
	
	def execute(self):
		try:
			self.result = (False, self.run())
		except BaseException as exc:
			self.result = (True, exc)
		finally:
			self.finished.emit()


class BackgroundTasks:
	def __init__(self):
		self._tasks = []

	def execute(self, worker: Task):
		thread = QThread()
		worker.moveToThread(thread)
		worker.finished.connect(thread.quit)
		worker.finished.connect(functools.partial(self._complete, thread, worker))
		thread.finished.connect(thread.deleteLater)
		thread.start()
		self._tasks.append((thread, worker))
	
	def _complete(self, thread: QThread, worker: Task):
		is_error, result_or_error = worker.result
		if is_error:
			worker.error_handler(result_or_error)
		else:
			worker.callback(result_or_error)

		worker.deleteLater()
		self._tasks.remove((thread, worker))


class FetchTask(Task[rss.Channel]):
	url: str

	def __init__(self, url):
		super().__init__()
		self.url = url

	def run(self) -> rss.Channel:
		response = requests.get(self.url, headers={
			"Accept": "application/rss+xml"
		})
		response.raise_for_status()

		content = response.text
		channel = rss.parse_feed(content)
		channel.ref = self.url
		return channel

	# TODO - implement these lol
	def handle_error(self, error: BaseException):
		if isinstance(error, requests.RequestException):
			pass
		elif isinstance(error, (rss.RSSError, xml.XMLEntityError)):
			pass
		else:
			pass

	def handle_result(self, result: rss.Channel):
		pass
