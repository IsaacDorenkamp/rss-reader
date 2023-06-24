import pytest

from ui.models import AggregateFeedModel
from reader.api.rss import Channel, Item


class MockGUID:
    value: str

    def __init__(self, value: str):
        self.value = value


class MockItem:
    __class__ = Item

    order: int
    guid: MockGUID

    def __init__(self, order):
        self.order = order
        self.guid = MockGUID(str(order))


@pytest.fixture
def odd_channel() -> Channel:
    return Channel(items=[
        MockItem(order=3),
        MockItem(order=5),
        MockItem(order=1)
    ])


@pytest.fixture
def even_channel() -> Channel:
    return Channel(items=[
        MockItem(order=4),
        MockItem(order=2)
    ])


def test_initial_sorting_succeeds(odd_channel: Channel, even_channel: Channel):
    model = AggregateFeedModel(
        sort_by=lambda element: element.order,
        feeds=[odd_channel, even_channel],
        fetch_batch_size=len(odd_channel.items) + len(even_channel.items)
    )

    result = list(model.items)
    for idx, item in enumerate(result):
        assert idx + 1 == item.order


def test_dynamic_sorting_succeeds(odd_channel: Channel, even_channel: Channel):
    model = AggregateFeedModel(
        sort_by=lambda element: element.order,
        feeds=[odd_channel],
        fetch_batch_size=len(odd_channel.items) + len(even_channel.items)
    )
    model.add(even_channel)

    for idx, item in enumerate(model.items):
        assert idx + 1 == item.order
