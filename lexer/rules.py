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

    def match(self, lexer):
        if not self.condition(lexer.peek()):
            return False, None
        return True, self.process(next(lexer))

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

    def match(self, lexer):
        values = []

        for rule in self.rules:
            is_match = self.match_once(rule, lexer, values)

            if not is_match and not rule.is_optional:
                return False, None

            while is_match and rule.is_repeatable:
                is_match = self.match_once(rule, lexer, values)

        return True, self.process(*values)

    def process(self, *values):
        return values

    @staticmethod
    def match_once(rule, lexer, values):
        drops = []

        # ignore whitespace and line breaks
        while isinstance(lexer.peek(), (tokens.WhiteSpace, tokens.EndOfLine)):
            drops.append(lexer.drop())

        is_match, value = rule.match(lexer)

        if not is_match:
            for token in drops:
                lexer.take_back(token)
            return False, None

        values.append(value)
        return True


class OrRule(Rule):
    """
    Abstract rule. Matches one of multiple rules.
    """

    rules = []

    def match(self, lexer):
        for rule in self.rules:
            is_match, value = rule.match(lexer)
            if is_match:
                return True, value
        return False, None
