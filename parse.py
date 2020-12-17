#!/usr/bin/env python3

import json
import datetime
import sys
from pathlib import Path

from tm.lexer import lex
from tm.parser.rules import Main


class DateTimeEncoder(json.JSONEncoder):

    def default(self, obj):
        if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return str(obj)
        return super(DateTimeEncoder, self).default(obj)


if __name__ == '__main__':
    is_match, data, _ = Main().match(None, lex(Path(sys.argv[1])))

    print(json.dumps(data, indent=4, sort_keys=True, cls=DateTimeEncoder))
