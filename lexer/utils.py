class UntilNoneIterator:
    """
    Generic iteretor for objects whose `__next__` returns None instead of raising
    `StopIteration`.

    >>> class Foo:
    ...     x = 4
    ...     def __next__(self):
    ...         if self.x == 0:
    ...             return None
    ...         self.x -= 1
    ...         return self.x
    ...     def __iter__(self):
    ...         return UntilNoneIterator(self)
    ...
    >>> print([i for i in Foo()])
    [3, 2, 1, 0]

    >>> [x for x in UntilNoneIterator(iter([1, 2, None]))]
    [1, 2]
    """

    def __init__(self, obj):
        self.obj = obj

    def __next__(self):
        value = next(self.obj)
        if value is None:
            raise StopIteration
        return value

    def __iter__(self):
        return self


class BufferedStream:
    """
    Wraps a stream object, providing a way to give back an item to the stream.
    Useful for adding look-ahead functionality to an iterator.

    >>> s = BufferedStream(iter(range(6)))
    >>> next(s)
    0
    >>> i = next(s); i
    1
    >>> s.take_back(i)
    >>> next(s)
    1
    >>> next(s)
    2
    >>> s.peek()
    3
    >>> s.peek()
    3
    >>> i = next(s); i
    3
    >>> j = next(s); j
    4
    >>> s.take_back(j); s.take_back(i)
    >>> next(s)
    3
    >>> next(s)
    4
    """

    def __init__(self, stream):
        self.buffer = []
        self.stream = stream

    def __next__(self):
        if self.buffer:
            return self.buffer.pop()
        return next(self.stream)

    def take_back(self, obj):
        self.buffer.append(obj)

    def peek(self):
        obj = next(self)
        self.take_back(obj)
        return obj
