from typing import Iterable

from PyQt5.QtCore import QObject, QThread, pyqtSignal
import requests
import functools
from typing import Optional, Callable, Any
import uuid

from reader.api import rss, xml


class Task(QObject):
	complete = pyqtSignal()

	thread: Optional[QThread]
	cbk: Optional[Callable[[], Any]]

	def __init__(self):
		super().__init__()
		self._id = uuid.uuid4()
		self.thread = None
		self.cbk = None

	def create_thread(self, cbk: Optional[Callable[[], Any]]) -> QThread:
		self.thread = thread = QThread()

		self.moveToThread(thread)

		thread.started.connect(self.run)
		self.complete.connect(self._end)

		thread.finished.connect(thread.deleteLater)
		return thread

	def _end(self):
		self.thread.quit()
		self.deleteLater()

		if self.cbk:
			self.cbk()

	@property
	def id(self):
		return self._id

	# Note: I would use abc's abstractmethod here but
	# there is a metaclass conflict between QObject
	# and abc.ABC, so only one can be applied. And
	# to leverage PyQT's threading system, we have no
	# choice but to choose to subclass QObject.
	def run(self):
		raise NotImplementedError()


class TaskManager:
	def __init__(self):
		self.running = []

	def start_task(self, task: Task):
		thread = task.create_thread(self._end_task)
		refs = (task, thread)
		thread.cbk = functools.partial(self._end_task, refs)
		self.running.append(refs)
		thread.start()

	def start_all(self, tasks: Iterable[Task]):
		for task in tasks:
			self.start_task(task)

	def _end_task(self, refs):
		self.running.remove(refs)


class FetchFeed(Task):
	success = pyqtSignal(rss.Channel)
	failure = pyqtSignal(Exception)
	complete = pyqtSignal()

	def __init__(self, url):
		super().__init__()
		self.url = url

		self.success.connect(self.complete.emit)
		self.failure.connect(self.complete.emit)

	def run(self):
		try:
			response = requests.get(self.url, headers={
				"Accept": "application/rss+xml"
			})
			response.raise_for_status()
		except requests.exceptions.RequestException as exc:
			self.failure.emit(exc)
			return

		content = response.text
		try:
			channel = rss.parse_feed(content)
			channel.ref = self.url
			self.success.emit(channel)
		except (rss.RSSError, xml.XMLEntityError) as exc:
			self.failure.emit(exc)
