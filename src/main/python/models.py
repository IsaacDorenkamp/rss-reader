from __future__ import annotations
import json
import time
from util import dateutil
from typing import Generator, Union, Any, Tuple, TypeVar, IO, Dict, List, Iterable

from reader.api import rss


class Multiple:
    def __init__(self, type_: Union[type, Multiple]):
        self.type = type_

    def expand(self, value):
        if isinstance(self.type, type) and issubclass(self.type, JSONModel):
            return tuple(item.to_dict() for item in value)
        elif isinstance(self.type, Multiple):
            return tuple(self.type.expand(item) for item in value)
        else:
            return tuple(value)


class JSONModelMeta(type):
    def __new__(mcs, name, bases, dct):
        if dct.get('abstract'):
            del dct['abstract']
            return super(JSONModelMeta, mcs).__new__(mcs, name, bases, dct)

        fields = {}

        for field_key, field_type in dct.items():
            if field_key.startswith('_'):
                continue
            if isinstance(field_type, (type, Multiple)):
                fields[field_key] = field_type

        if '_required' not in dct:
            dct['_required'] = ()

        dct['__json_fields__'] = fields

        return super(JSONModelMeta, mcs).__new__(mcs, name, bases, dct)


class JSONModel(metaclass=JSONModelMeta):
    abstract = True
    __json_fields__: Dict[str, Union[type, Multiple]]
    _required: List[str]

    def __init__(self, **kw):
        for key, value in kw.items():
            setattr(self, key, value)

    def to_dict_items(self) -> Generator[Tuple[str, Any], None, None]:
        for key, value_type in self.__json_fields__.items():
            value = getattr(self, key)
            if value is None:
                yield key, None
                continue

            if isinstance(value_type, Multiple):
                yield key, value_type.expand(value)
            elif isinstance(value_type, JSONModel):
                yield key, value.to_dict()
            else:
                yield key, value

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.to_dict_items())

    @classmethod
    def from_string(cls, string: str) -> JSONModel:
        return cls.from_dict(json.loads(string))

    @classmethod
    def load(cls, source: IO[str]) -> JSONModel:
        return cls.from_dict(json.load(source))

    def to_string(self) -> str:
        return json.dumps(self.to_dict())

    def save(self, dest: IO[str]):
        json.dump(self.to_dict(), dest)

    @staticmethod
    def to_multiple(items: Iterable[J]) -> Tuple[Dict[str, Any]]:
        return tuple(item.to_dict() for item in items)

    @classmethod
    def from_dict(cls, source: dict) -> JSONModel:
        values = {}
        for key, value_type in cls.__json_fields__.items():
            value = source.get(key)
            result = parse_value(value_type, value)
            if result is None and key in cls._required:
                raise ValueError("Field '%s' is required and cannot be None." % key)
            values[key] = result

        return cls(**values)

    @classmethod
    def load_multiple(cls, source: IO[str]):
        array = json.load(source)
        assert isinstance(array, (list, tuple)), "File does not define an array"
        return tuple(cls.from_dict(source) for source in array)

    @staticmethod
    def save_multiple(items: Iterable[J], dest: IO[str]):
        return json.dump([item.to_dict() for item in items], dest)


J = TypeVar('J', bound=JSONModel)


def parse_value(json_type_def: Union[type, Multiple, J], value: Any) -> Any:
    if value is None:
        return None
    elif isinstance(json_type_def, Multiple):
        return tuple(parse_value(json_type_def.type, item) for item in value)
    elif hasattr(json_type_def, '__json_fields__'):
        return json_type_def.from_dict(value)
    else:
        return json_type_def(value)


class FeedDefinition(JSONModel):
    _required = ['url', 'last_retrieved']

    nickname: str = str
    url: str = str
    cache_key: str = str
    last_retrieved: int = int  # timestamp when the feed was last retrieved, a rounded result of time.time().
    ttl: int = int  # TTL in seconds
    skip_days: List[int] = list
    skip_hours: List[int] = list

    def update(self, channel: rss.Channel):
        self.nickname = channel.title
        self.ttl = (channel.ttl or 0) * 60
        self.skip_days = [dateutil.WEEKDAYS[day] for day in (channel.skip_days or []) if day in dateutil.WEEKDAYS.keys()]
        self.skip_hours = [hour % 24 for hour in (channel.skip_hours or [])]

    @staticmethod
    def from_channel(channel):
        return FeedDefinition(nickname=channel.title, url=channel.ref, cache_key=None, last_retrieved=int(time.time()),
                              ttl=(channel.ttl or 0) * 60,
                              skip_days=[dateutil.WEEKDAYS[day] for day in (channel.skip_days or []) if day in
                                         dateutil.WEEKDAYS.keys()],
                              skip_hours=[hour % 24 for hour in channel.skip_hours or []])
