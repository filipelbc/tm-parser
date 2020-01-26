from abc import ABC, abstractmethod

import tokens


class Rule(ABC):
    """
    Abstract base rule class.
    """
    is_optional = False
    is_repeatable = False

    @abstractmethod
    def match(self, token_s):
        """
        @token_s A rewindable stream of tokens.

        Returns a tuple:
        - bool indicating whether the rule matched;
        - the value matched;
        - the count of tokens consumed.

        Note that if a rule does not match, it must not consume any token.
        """
        return False, None, 0


class BottomRule(Rule, ABC):
    """
    Abstract rule. Matches a single token of the specified type.

    @type Must be suitable to serve as the second argument of the isinstance()
          builtin.
    """

    types = None

    def match(self, token_s):
        if not self.condition(token_s.peek()):
            return False, None, 0
        return True, self.process(next(token_s)), 1

    def condition(self, token):
        return isinstance(token, self.types)

    def process(self, token):
        return token.value


class E(BottomRule):
    """
    This rule flags the expected end of input, where the token is None.
    """

    types = type(None)

    def process(self, token):
        return None


class V(BottomRule):
    """
    This rule matches a token of the specified type and returns its value.
    """

    def __init__(self, types):
        """
        @type Must be suitable to serve as the second argument of the
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
    This rule matches the specified sequence of caracters.
    """

    def __init__(self, chars):
        self.chars = chars

    def match(self, token_s):
        for i, char in enumerate(self.chars):
            t = next(token_s)
            if not (isinstance(t, tokens.Character) and t.value == char):
                token_s.rewind(i + 1)
                return False, None, 0

        return True, self.chars, len(self.chars)


class AndRule(Rule):
    """
    Abstract rule. Matches a sequence of rules.

    @skip_tokens Tuple of token types to skip before each rule.  Normally used
                 to make whitespace between tokens mandatory.

    Matches if the rules in @rules match one after the other. If @skip_tokens
    is set, there must be at least one token of these kinds between each rule.
    These tokens are also skipped in the very beginning, altough their presence
    is not mandatory.
    """
    skip_tokens = (
        tokens.WhiteSpace,
        tokens.Comment,
        tokens.EndOfLine,
    )
    rules = []

    def match(self, token_s):
        values = []
        count = 0

        for i, rule in enumerate(self.rules):
            is_match, i_count = self.match_once(rule, token_s, values, is_first=(i == 0))
            count += i_count

            if not is_match and not rule.is_optional:
                token_s.rewind(count)
                return False, None, 0

            while is_match and rule.is_repeatable:
                is_match, i_count = self.match_once(rule, token_s, values)
                count += i_count

        return True, self.process(*values), count

    def process(self, *values):
        return values or None

    @classmethod
    def match_once(cls, rule, token_s, value_acc, is_first=False):
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

        while isinstance(token_s.peek(), cls.skip_tokens):
            next(token_s)
            s_count += 1

        if cls.skip_tokens and s_count == 0 and not is_first:
            token_s.rewind(s_count)
            return False, 0

        is_match, value, count = rule.match(token_s)

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

    def match(self, token_s):
        for rule in self.rules:
            is_match, value, count = rule.match(token_s)
            if is_match:
                return True, value, count
        return False, None, 0
