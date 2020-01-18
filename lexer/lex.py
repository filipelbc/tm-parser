#!/usr/bin/env python3

import sys
from pathlib import Path

from utils import UntilNoneIterator
from lexer import Lexer

if __name__ == '__main__':
    lexer = Lexer(Path(sys.argv[-1]))

    for token, location in UntilNoneIterator(lexer):
        print(token)
