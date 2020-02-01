from pathlib import Path
from io import StringIO


class Location:
    """
    Holds the information about the position of a character (in practice, the
    first character of a token) in a file or string.
    """

    def __init__(self, path, line_num, column=0):
        self.path = path
        self.line_num = line_num
        self.column = column

    def __repr__(self):
        """
        >>> Location("foo.tjp", 2, 10)
        Location('foo.tjp', 2, 10)
        """
        return '%s(%r, %s, %s)' % (self.__class__.__name__,
                                   self.path,
                                   self.line_num,
                                   self.column)

    def move_to(self, column):
        """
        Creates a copy of the location, but uses the new column.
        """
        return Location(self.path, self.line_num, column)


class LineStream:
    """
    Provides an interface to get a stream of lines from either a file or a
    string. Lines are provided together with their corresponding location.

    >>> s = LineStream('foo\\nbar\\nbum')
    >>> next(s)
    ('foo\\n', Location(None, 1, 0))

    >>> next(s)
    ('bar\\n', Location(None, 2, 0))

    >>> next(s)
    ('bum', Location(None, 3, 0))

    >>> next(s)
    """

    def __init__(self, source):
        self.file = None
        if isinstance(source, str):
            self.path = None
            self.file = StringIO(source)
        elif isinstance(source, Path):
            self.path = source
            self.file = open(source, 'r')
        else:
            raise ValueError(source)
        self.line_num = 0

    def __next__(self):
        line = self.file.readline()
        if not line:
            return None
        self.line_num += 1
        return (line, Location(self.path, self.line_num))

    def __del__(self):
        if self.file is not None:
            self.file.close()
