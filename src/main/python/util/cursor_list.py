import typing


T = typing.TypeVar('T')


class CursorList(list, typing.List[T]):
    def __init__(self, initial: typing.Optional[typing.Iterable] = None):
        list.__init__(self, initial)
        self._cursor = -1

    def remove(self, x):
        list.remove(self, x)
        if self._cursor > len(self):
            self._cursor = len(self)

    def clear(self):
        list.clear(self)
        self._cursor = -1

    def reverse(self):
        list.reverse(self)
        self._cursor = len(self) - (self._cursor + 1)

    def pop(self, index: typing.Optional[int] = None):
        list.pop(self, index)
        if self._cursor >= index:
            self._cursor -= 1

    def insert(self, index: int, item):
        list.insert(self, index, item)
        if self._cursor >= index:
            self._cursor += 1

    def copy(self):
        base = list.copy(self)
        return CursorList(base)

    def peek_next(self):
        if 0 <= self._cursor + 1 < len(self):
            return self[self._cursor + 1]
        else:
            raise IndexError("Cursor out of range")

    def peek_previous(self):
        if 0 <= self._cursor - 1 < len(self):
            return self[self._cursor - 1]
        else:
            raise IndexError("Cursor out of range")

    def next(self):
        if self._cursor + 1 < len(self):
            self._cursor += 1
            return self[self._cursor]
        else:
            raise IndexError("Cursor out of range")

    def __next__(self):
        return self.next()

    def previous(self):
        if self._cursor > 0:
            self._cursor -= 1
            return self[self._cursor]
        else:
            raise IndexError("Cursor out of range")

    def __delitem__(self, indexes):
        list.__delitem__(self, indexes)
        if isinstance(indexes, int):
            if self._cursor >= indexes:
                self._cursor -= 1
        elif isinstance(indexes, slice):
            # optimize performance for reverse slices
            if indexes.step < 0:
                step = -indexes.step
                start = indexes.stop + step
                stop = indexes.start + step
            else:
                step = indexes.step
                start = indexes.start
                stop = indexes.stop

            before_cursor = 0
            for index in range(start, stop, step):
                if index <= self._cursor:
                    before_cursor += 1
                else:
                    break

            self._cursor -= before_cursor

    def __reversed__(self):
        rev = CursorList(self.copy())
        rev._cursor = self._cursor
        rev.reverse()
        return rev

    @property
    def cursor(self):
        return self._cursor

    @cursor.setter
    def cursor(self, value):
        if 0 <= value <= len(self):
            self._cursor = value
        else:
            raise IndexError("Cursor out of range")

    @property
    def has_next(self):
        return self.cursor + 1 < len(self)

    @property
    def has_previous(self):
        return self._cursor - 1 >= 0
