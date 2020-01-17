class UntilNoneIterator:
    """
    Generic iteretor for objects whose __next__ returns None instead of raising
    StopIteration.

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
