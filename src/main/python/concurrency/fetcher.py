import functools
from typing import Any, Callable, Dict, Optional, Set, Union, Tuple, Iterable
import uuid

from .tasks import TaskManager, FetchFeed
from reader.api.rss import Channel


class Fetcher:
    callbacks: Dict[uuid.UUID, Callable[[Channel], Any]]
    task_manager: TaskManager

    _groups: Dict[uuid.UUID, Tuple[Set[uuid.UUID], Dict[str, Union[Channel, Exception]],
                  Callable[[Dict[str, Union[Channel, Exception]]], Any]]]
    _task_to_group: Dict[uuid.UUID, uuid.UUID]

    def __init__(self, task_manager: TaskManager = None):
        self.callbacks = {}

        self._groups = {}
        self._task_to_group = {}

        if task_manager is None:
            self.task_manager = TaskManager()
        else:
            self.task_manager = task_manager

    def fetch_all(self, urls: Iterable[str], cbk: Callable[[Dict[str, Union[Channel, Exception]]], Any]):
        group_id = uuid.uuid4()

        task_ids: Set[uuid.UUID] = set()
        results: Dict[str, Union[Channel, Exception]] = {}

        self._groups[group_id] = (task_ids, results, cbk)

        for url in urls:
            self.fetch(url, None, group_id)

    def fetch(self, url: str, callback: Optional[Callable[[Union[Channel, Exception]], Any]] = None,
              group: Optional[uuid.UUID] = None) -> Optional[FetchFeed]:
        """
        :param url: The URL to fetch.
        :param callback: The function to call if the fetch succeeds. Accepts the channel as a parameter.
        :param group: The group of fetch requests that this call belongs to. May be None if this fetch is an individual
            request.
        :return: The fetch task if one was started, or None if one is already in progress.
        """
        task = FetchFeed(url)

        cbk = functools.partial(self.__complete, group, task.id, url)
        task.success.connect(cbk)
        task.failure.connect(cbk)

        if callback:
            self.callbacks[task.id] = callback

        if group:
            if group in self._groups:
                self._groups[group][0].add(task.id)
            else:
                raise AttributeError("Group '{}' has not been registered".format(str(task.id)))

        self.task_manager.start_task(task)
        return task

    def __complete(self, group: Optional[uuid.UUID], task_id: uuid.UUID, url: str,  result: Union[Channel, Exception]):
        if group:
            group_data = self._groups[group]
            group_data[0].remove(task_id)
            group_data[1][url] = result

            if not self._groups[group][0]:
                group_data[2](group_data[1])

        cbk = self.callbacks.get(task_id)
        if cbk:
            cbk(result)
            del self.callbacks[task_id]
