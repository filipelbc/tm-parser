from abc import ABC, abstractmethod, abstractstaticmethod

from ..lexer import tokens


class Rule(ABC):
    """
    Abstract base rule class.

    A rule "matches" the tokens from a token stream and "processes" the matched
    values together with a context, returning the processed data.
    """
    is_optional = False
    is_repeatable = False

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

    @abstractstaticmethod
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

    def __init__(self, types):
        """
        @types Must be suitable to serve as the second argument of the
               isinstance() builtin.
        """
        self.types = types


class N(BottomRule):
    """
    This rule matches a Name token that contains the specified name.
    """

    types = tokens.Name

    def __init__(self, name):
        self.name = name

    def condition(self, token):
        return super().condition(token) and token.value == self.name


class C(BottomRule):
    """
    This rule matches the specified sequence of characters and returns it.
    """

    def __init__(self, chars):
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

    @is_skip_optional Whether or not skipping tokens is optional.

    These two attribubes are normally used to make whitespace between tokens
    mandatory.
    """
    tokens_to_skip = (
        tokens.WhiteSpace,
        tokens.Comment,
        tokens.EndOfLine,
    )
    is_skip_optional = False

    rules = []

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

    @classmethod
    def match_once(cls, rule, x, token_s, value_acc, is_first=False):
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

        while isinstance(token_s.peek(), cls.tokens_to_skip):
            next(token_s)
            s_count += 1

        if not cls.is_skip_optional and cls.tokens_to_skip and s_count == 0 and not is_first:
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

    def match(self, x, token_s):
        for rule in self.rules:
            is_match, value, count = rule.match(x, token_s)
            if is_match:
                return True, self.process(x, value), count
        return False, None, 0

    @staticmethod
    def process(x, value):
        return value
