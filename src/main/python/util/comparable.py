from abc import ABCMeta, abstractmethod
import typing


T = typing.TypeVar('T')


class Comparable(typing.Protocol[T]):
    def __lt__(self: T, other: T) -> typing.Union[bool, 'NotImplemented']:
        pass


def keyed(sequence: typing.Sequence[T], key: typing.Callable[[T], Comparable]):
    return [key(item) for item in sequence]
