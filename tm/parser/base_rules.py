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

    def __init__(self):
        super().__init__()

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

    def __init__(self, types):
        """
        @types Must be suitable to serve as the second argument of the
               isinstance() builtin.
        """
        super().__init__()
        self.types = types


class N(BottomRule):
    """
    This rule matches a Name token that contains the specified name.
    """

    types = tokens.Name

    def __init__(self, name):
        super().__init__()
        self.name = name

    def condition(self, token):
        return super().condition(token) and token.value == self.name


class C(BottomRule):
    """
    This rule matches the specified sequence of characters and returns it.
    """

    def __init__(self, chars):
        super().__init__()
        self.chars = chars

    def match(self, x, token_s):
        for i, char in enumerate(self.chars):
            t = next(token_s)
            if not (isinstance(t, tokens.Character) and t.value == char):
                token_s.rewind(i + 1)
                return False, None, 0

        return True, self.chars, len(self.chars)


class AndRule(Rule):
    """
    Abstract rule. Matches a sequence of rules, one after the other.

    Optionaly skips some tokens between these rules.

    @tokens_to_skip Which token types to skip before each rule.

    These two attribubes are normally used to make whitespace between tokens
    mandatory.
    """
    tokens_to_skip = (tokens.WhiteSpace, tokens.EndOfLine)

    rules = []

    def __init__(self, optional_skip=False, **kwargs):
        """
        @is_skip_optional Whether or not skipping tokens is optional.
        """
        super().__init__(**kwargs)
        self.is_skip_optional = optional_skip

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
                  sequence, in which case skipping is optional.

        Returns a tuple:
        - boolean indicating whether the rule matched
        - the count of consumed tokens

        Note that the matched value is added to an accumulator for convenience.
        """
        s_count = 0

        while isinstance(token_s.peek(), self.tokens_to_skip):
            next(token_s)
            s_count += 1

        if not self.is_skip_optional and self.tokens_to_skip and s_count == 0 and not is_first:
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
