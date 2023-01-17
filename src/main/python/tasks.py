from PyQt5.QtCore import QObject, QThread, pyqtSignal
import requests
import functools

from reader.api import rss, xml

class Task(QObject):
	complete = pyqtSignal()

class TaskManager:
	def __init__(self):
		self.running = []

	def start_task(self, task):
		thread = task.create_thread()
		refs = (task, thread)
		self.running.append(refs)
		task.complete.connect(functools.partial(self._end_task, refs))
		thread.start()

	def _end_task(self, refs):
		self.running.remove(refs)

class FetchFeed(Task):
	success = pyqtSignal(rss.Channel)
	failure = pyqtSignal(Exception)
	complete = pyqtSignal()

	def __init__(self, url):
		super().__init__()
		self.url = url

		self.success.connect(self._finish)
		self.failure.connect(self._finish)

	def _finish(self, *args):
		self.complete.emit()

	def create_thread(self):
		thread = QThread()

		self.moveToThread(thread)

		thread.started.connect(self.run)
		self.complete.connect(thread.quit)
		self.complete.connect(self.deleteLater)

		thread.finished.connect(thread.deleteLater)
		return thread

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
			self.success.emit(channel)
		except (rss.RSSError, xml.XMLEntityError) as exc:
			self.failure.emit(exc)