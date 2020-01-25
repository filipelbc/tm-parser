import tokens


class Rule:
    """
    Abstract base rule class.
    """
    is_optional = False
    is_repeatable = False


class BottomRule(Rule):
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


class AndRule(Rule):
    """
    Abstract rule. Matches a sequence of rules.
    """

    rules = []

    def match(self, token_s):
        values = []
        count = 0

        for rule in self.rules:
            is_match, i_count = self.match_once(rule, token_s, values)
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

    @staticmethod
    def match_once(rule, token_s, value_acc):
        """
        @value_acc Accumulator into which to put the matched value.

        Returns a tuple:
        - boolean indicating whether the rule matched
        - the count of consumed tokens

        Note that the matched value is added to an accumulator for convenience.
        """
        w_count = 0

        # ignore whitespace and line breaks
        while isinstance(token_s.peek(), (tokens.WhiteSpace, tokens.EndOfLine)):
            next(token_s)
            w_count += 1

        is_match, value, count = rule.match(token_s)

        if not is_match:
            token_s.rewind(w_count)
            return False, 0

        value_acc.append(value)
        return True, w_count + count


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
