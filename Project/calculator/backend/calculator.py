"""A small decimal expression parser. User input is never executed as code."""

import re
from decimal import Decimal, DecimalException, Underflow, localcontext


class CalculationError(ValueError):
    """An expression cannot be calculated."""


TOKEN = re.compile(r"(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?|[+\-*/^()%]")
MAX_MAGNITUDE = Decimal("1e100")
MIN_MAGNITUDE = Decimal("1e-100")


def checked(value: Decimal) -> Decimal:
    magnitude = value.copy_abs()
    if not value.is_finite() or magnitude > MAX_MAGNITUDE:
        raise CalculationError("The result is too large (maximum magnitude: 1e100).")
    if value and magnitude < MIN_MAGNITUDE:
        raise CalculationError("The result is too small (minimum magnitude: 1e-100).")
    return value


class Parser:
    def __init__(self, expression: str):
        self.tokens: list[str] = []
        self.position = 0
        self.depth = 0
        position = 0
        while position < len(expression):
            if expression[position].isspace():
                position += 1
                continue
            match = TOKEN.match(expression, position)
            if match is None:
                raise CalculationError(f"Unexpected character: {expression[position]!r}.")
            self.tokens.append(match.group())
            position = match.end()
        if len(self.tokens) > 128:
            raise CalculationError("The expression has too many operations.")

    def peek(self) -> str:
        return self.tokens[self.position] if self.position < len(self.tokens) else ""

    def take(self) -> str:
        token = self.peek()
        if not token:
            raise CalculationError("The expression is incomplete.")
        self.position += 1
        return token

    def expression(self) -> Decimal:
        value = self.term()
        while self.peek() in ("+", "-"):
            operator = self.take()
            right = self.term()
            value = checked(value + right if operator == "+" else value - right)
        return value

    def term(self) -> Decimal:
        value = self.unary()
        while self.peek() in ("*", "/"):
            operator = self.take()
            right = self.unary()
            if operator == "/" and right == 0:
                raise CalculationError("You can't divide by zero.")
            value = checked(value * right if operator == "*" else value / right)
        return value

    def unary(self) -> Decimal:
        if self.peek() in ("+", "-"):
            operator = self.take()
            value = self.unary()
            return -value if operator == "-" else value
        return self.power()

    def power(self) -> Decimal:
        value = self.postfix()
        if self.peek() == "^":
            self.take()
            exponent = self.unary()
            if exponent != exponent.to_integral_value() or abs(exponent) > 100:
                raise CalculationError("Use a whole-number exponent between -100 and 100.")
            if value == 0 and exponent < 0:
                raise CalculationError("You can't divide by zero.")
            if value == 0 and exponent == 0:
                raise CalculationError("Zero to the power of zero is undefined.")
            value = checked(value ** int(exponent))
        return value

    def postfix(self) -> Decimal:
        value = self.primary()
        while self.peek() == "%":
            self.take()
            value = checked(value / 100)
        return value

    def primary(self) -> Decimal:
        token = self.take()
        if token == "(":
            self.depth += 1
            if self.depth > 24:
                raise CalculationError("Use no more than 24 levels of parentheses.")
            value = self.expression()
            if self.peek() != ")":
                raise CalculationError("A closing parenthesis is missing.")
            self.take()
            self.depth -= 1
            return value
        if token in ("+", "-", "*", "/", "^", "%", ")"):
            raise CalculationError(f"Expected a number, but found {token!r}.")
        return checked(Decimal(token))


def calculate(expression: str) -> str:
    """Evaluate +, -, ×, ÷, parentheses, postfix %, and integer powers."""
    if not expression.strip():
        raise CalculationError("Enter an expression first.")
    if len(expression) > 256:
        raise CalculationError("Keep expressions to 256 characters or fewer.")
    expression = expression.translate(str.maketrans({"×": "*", "÷": "/", "−": "-"}))
    expression = expression.replace("**", "^")
    try:
        with localcontext() as context:
            context.prec = 28
            context.Emax = 999
            context.Emin = -999
            context.traps[Underflow] = True
            parser = Parser(expression)
            value = checked(+parser.expression())
            if parser.peek():
                raise CalculationError(f"Unexpected token: {parser.peek()!r}. Use × between factors.")
            if value == 0:
                return "0"
            if abs(value) >= Decimal("1e16") or abs(value) < Decimal("1e-8"):
                return format(value.normalize(), "E").replace("E", "e")
            result = format(value, "f")
            return result.rstrip("0").rstrip(".") if "." in result else result
    except DecimalException as exc:
        raise CalculationError("The result is outside the supported numeric range.") from exc
