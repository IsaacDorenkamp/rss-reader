import pytest

from util.cursor_list import CursorList


@pytest.fixture
def source_data() -> CursorList:
    return CursorList(['a', 'b', 'c'])


@pytest.fixture
def large_source_data() -> CursorList:
    return CursorList(['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j'])


def test_next(source_data: CursorList):
    assert next(source_data) == 'a'
    assert next(source_data) == 'b'
    assert next(source_data) == 'c'
    with pytest.raises(IndexError):
        next(source_data)


def test_reverse(source_data: CursorList):
    source_data.reverse()
    assert source_data.cursor == len(source_data)


def test_previous(source_data: CursorList):
    source_data.cursor = len(source_data)
    assert source_data.previous() == 'c'
    assert source_data.previous() == 'b'
    assert source_data.previous() == 'a'
    with pytest.raises(IndexError):
        source_data.previous()


def test_pop(source_data: CursorList):
    source_data.cursor = len(source_data)
    source_data.pop(0)
    assert len(source_data) == 2
    assert source_data.cursor == len(source_data)


def test_delete_before_cursor(large_source_data: CursorList):
    t_list = large_source_data
    t_list.cursor = 5
    del t_list[0]
    assert t_list.cursor == 4


def test_delete_after_cursor(large_source_data: CursorList):
    t_list = large_source_data
    t_list.cursor = 5
    del t_list[6]
    assert t_list.cursor == 5


def test_delete_slice(large_source_data: CursorList):
    t_list = large_source_data
    t_list.cursor = 4
    del t_list[3:10:2]
    assert t_list == ['a', 'b', 'c', 'e', 'g', 'i']
    assert t_list.cursor == 3


def test_delete_reverse_slice(large_source_data: CursorList):
    t_list = large_source_data
    t_list.cursor = 4
    del t_list[9:1:-2]
    assert t_list == ['a', 'b', 'c', 'e', 'g', 'i']
    assert t_list.cursor == 3


def test_insert(source_data: CursorList):
    source_data.cursor = 0
    source_data.insert(0, 'z')
    assert source_data.cursor == 1
