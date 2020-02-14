from enum import Flag
from abc import ABC, abstractmethod

from ..lexer import tokens


class Rule(ABC):
    """
    Abstract base rule class.

    A rule "matches" the tokens from a token stream and "processes" the matched
    values together with a context, returning the processed data.
    """

    def __init__(self, optional=False, repeatable=False):
        self.is_optional = optional
        self.is_repeatable = repeatable

    @abstractmethod
    def match(self, x, token_s):
        """
        @x Aka. "context". Object in which to accumulate the parsed data.

        @token_s A rewindable stream of tokens.

        Returns a tuple:
        - bool indicating whether the rule matched;
        - the value matched after being processed;
        - the count of tokens consumed.

        Note that if a rule does not match, it must not consume any token.
        """
        return False, self.process(x, None), 0

    @staticmethod
    @abstractmethod
    def process(x, *args):
        """
        @args The matched values

        @x Aka. "context". Object in which to accumulate the parsed data.

        Override this method in order to process the matched values before
        returning them and build up the context.
        """
        return None


class BottomRule(Rule, ABC):
    """
    Abstract rule. Matches a single token of the specified type.

    @type Must be suitable to serve as the second argument of the isinstance()
          builtin.

    Rules of this type just ignore the context and return the matched value.
    """

    types = None

    def match(self, x, token_s):
        if not self.condition(token_s.peek()):
            return False, None, 0
        return True, self.process(x, next(token_s)), 1

    def condition(self, token):
        return isinstance(token, self.types)

    @staticmethod
    def process(x, token):
        return token.value if token else None


class E(BottomRule):
    """
    This rule flags the expected end of input, where the token is None.
    """

    types = type(None)


class V(BottomRule):
    """
    This rule matches a token of the specified type and returns its value.
    """

    def __init__(self, types, **kwargs):
        """
        @types Must be suitable to serve as the second argument of the
               isinstance() builtin.
        """
        super().__init__(**kwargs)
        self.types = types


class N(BottomRule):
    """
    This rule matches a Name token that contains the specified name.
    """

    types = tokens.Name

    def __init__(self, name, **kwargs):
        super().__init__(**kwargs)
        self.name = name

    def condition(self, token):
        return super().condition(token) and token.value == self.name


class C(BottomRule):
    """
    This rule matches the specified sequence of characters and returns it.
    """

    def __init__(self, chars, **kwargs):
        super().__init__(**kwargs)
        self.chars = chars

    def match(self, x, token_s):
        for i, char in enumerate(self.chars):
            t = next(token_s)
            if not (isinstance(t, tokens.Character) and t.value == char):
                token_s.rewind(i + 1)
                return False, None, 0

        return True, self.chars, len(self.chars)


class SkipBehavior(Flag):
    NONE = 0
    FIRST = 1
    OPTIONAL_FIRST = 2
    MIDDLE = 4
    OPTIONAL_MIDDLE = 8

    NORMAL = OPTIONAL_FIRST | MIDDLE
    OPTIONAL = OPTIONAL_FIRST | OPTIONAL_MIDDLE
    NO_SKIP = NONE

    def validate(self, first, count):
        if first:
            optional = self.OPTIONAL_FIRST in self
            p = self.FIRST in self
        else:
            optional = self.OPTIONAL_MIDDLE in self
            p = self.MIDDLE in self

        return optional or (count == 0 and not p) or (count > 0 and p)


class AndRule(Rule):
    """
    Abstract rule. Matches a sequence of rules, one after the other.

    @whitespace_tokens Which tokens types are considered whitespace and might
                       be skipped over.

    @skip_behavior The desired behavior regarding skipping of
                   @whitespace_tokens.
    """
    whitespace_tokens = (tokens.WhiteSpace, tokens.EndOfLine)
    skip_behavior = SkipBehavior.NORMAL

    rules = []

    def __init_subclass__(cls, **kwargs):
        """
        Provides a rules defintion shortcut on @rules. Also provisions for
        recursivity (see 'Self' and 'make_rule' below).
        """
        super().__init_subclass__(**kwargs)
        cls.rules = [make_rule(r, k=OrRule, s=cls) for r in cls.rules]

    def match(self, x, token_s):
        values = []
        count = 0

        for i, rule in enumerate(self.rules):
            is_match, i_count = self.match_once(rule, x, token_s, values, is_first=(i == 0))
            count += i_count

            if not is_match and not rule.is_optional:
                token_s.rewind(count)
                return False, None, 0

            while is_match and rule.is_repeatable:
                is_match, i_count = self.match_once(rule, x, token_s, values)
                count += i_count

        return True, self.process(x, *values), count

    @staticmethod
    def process(x, *args):
        return args or None

    def match_once(self, rule, x, token_s, value_acc, is_first=False):
        """
        @value_acc Accumulator into which to put the matched value.

        @is_first Indicates whether we are at the very beginning of the rule
                  sequence. Used for the whitespace skipping behavior.

        Returns a tuple:
        - boolean indicating whether the rule matched
        - the count of consumed tokens

        Note that the matched value is added to an accumulator for convenience.
        """
        s_count = 0

        while isinstance(token_s.peek(), self.whitespace_tokens):
            next(token_s)
            s_count += 1

        if not self.skip_behavior.validate(is_first, s_count):
            token_s.rewind(s_count)
            return False, 0

        is_match, value, count = rule.match(x, token_s)

        if not is_match:
            token_s.rewind(s_count)
            return False, 0

        value_acc.append(value)
        return True, s_count + count


class OrRule(Rule):
    """
    Abstract rule. Matches one of multiple rules.
    """

    rules = []

    def __init_subclass__(cls, **kwargs):
        """
        Provides a rules defintion shortcut on @rules.
        """
        super().__init_subclass__(**kwargs)
        cls.rules = [make_rule(r) for r in cls.rules]

    def match(self, x, token_s):
        for rule in self.rules:
            is_match, value, count = rule.match(x, token_s)
            if is_match:
                return True, self.process(x, value), count
        return False, None, 0

    @staticmethod
    def process(x, value):
        return value


class Self:
    """
    Marker to allow recursive rules.
    """
    pass


def make_rule(r, k=AndRule, n='R', s=None):
    """
    Creates a new rule type from @r and returns an instance.

    If @r is already a rule, it is simply returned.

    If @r is a list, @k is used as base class and @n is used as type name.
    Otherwise they are ignored.
    """
    if isinstance(r, list):
        return type(n, (k,), dict(rules=r))()

    elif isinstance(r, str):
        return N(r) if r.isidentifier() else C(r)

    elif issubclass(r, tokens.Token):
        return V(r)

    elif r is Self:
        return s(optional=True, repeatable=True)

    return r
