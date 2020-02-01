from .lexer import Lexer
from .utils import RewindableStream, TupleFilter


def lex(source):
    """
    Produces a rewindable stream of tokens from the given source.
    """
    return RewindableStream(TupleFilter(Lexer(source), '_location'))
