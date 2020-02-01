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


class RewindableStream:
    """
    Wraps a stream object, providing a way to give back an item to the stream.
    Useful for adding look-ahead functionality to an iterator.

    >>> s = RewindableStream(iter(range(6)))
    >>> next(s)
    0
    >>> next(s)
    1
    >>> s.rewind(1)
    >>> next(s)
    1
    >>> next(s)
    2
    >>> s.peek()
    3
    >>> s.peek()
    3
    >>> next(s)
    3
    >>> next(s)
    4
    >>> s.rewind(2)
    >>> next(s)
    3
    >>> next(s)
    4
    """

    def __init__(self, stream):
        self.given = []
        self.peeked = []
        self.stream = stream

    def __next__(self):
        if self.peeked:
            o = self.peeked.pop()
        else:
            o = next(self.stream)

        self.given.append(o)
        return o

    def peek(self):
        if self.peeked:
            return self.peeked[-1]

        o = next(self.stream)
        self.peeked.append(o)
        return o

    def rewind(self, n):
        assert len(self.given) >= n

        for _ in range(n):
            self.peeked.append(self.given.pop())

    def flush(self):
        self.given = []


class TupleFilter:
    """
    Modifies a stream of tuples turning it into a stream of objects.  The first
    element of the tuple is considered the main object. The remaining elements
    become attributes of this object.

    In the test below, Bar is some object; Foo is a stream of tuples whose
    first element is of the Bar class.

    >>> class Bar:
    ...     def __init__(self, v):
    ...         self.v = v
    ...
    >>> class Foo:
    ...     s = [(Bar(1), 'b'), (Bar(2), 'd'), (Bar(3), 'f'), None]
    ...     i = 0
    ...     def __next__(self):
    ...         t = self.s[self.i]
    ...         self.i += 1
    ...         return t
    ...
    >>> s = TupleFilter(Foo(), 'alt')
    >>> i = next(s); print(i.v, i.alt)
    1 b
    >>> i = next(s); print(i.v, i.alt)
    2 d
    >>> i = next(s); print(i.v, i.alt)
    3 f
    >>> i = next(s); print(i)
    None
    """

    def __init__(self, stream, *attr_names):
        """
        @stream The stream to be filtered
        @attr_names The names to use for the attributes
        """
        self.stream = stream
        self.attr_names = attr_names

    def __next__(self):
        tup = next(self.stream)
        if tup is None:
            return None

        obj, *attr_values = tup
        assert len(self.attr_names) == len(attr_values)

        for name, value in zip(self.attr_names, attr_values):
            setattr(obj, name, value)

        return obj
