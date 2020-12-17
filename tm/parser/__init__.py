from tm.lexer import lex
from tm.parser.rules import Main
from tm.parser.context import Context


def parse(source):
    x = Context()
    Main().match(x, lex(source))
    return x.project
