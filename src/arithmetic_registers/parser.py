from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .registers import RegisterStore


class ParserError(ValueError):
    pass


@dataclass
class ExpressionParser:
    source: str
    index: int = 0

    def parse(self) -> tuple[str, Any]:
        node = self._parse_expression()
        if self._peek() is not None:
            raise ParserError(f"Unexpected token at position {self.index}: {self._peek()!r}")
        return node

    def evaluate(self, registers: RegisterStore | dict[str, float] | None = None) -> float:
        node = self.parse()
        store = registers if registers is not None else {}
        return self._eval(node, store)

    def _parse_expression(self) -> tuple[str, Any]:
        node = self._parse_term()
        while self._peek() in {"+", "-"}:
            op = self._next()
            rhs = self._parse_term()
            node = ("binary", op, node, rhs)
        return node

    def _parse_term(self) -> tuple[str, Any]:
        node = self._parse_factor()
        while self._peek() in {"*", "/"}:
            op = self._next()
            rhs = self._parse_factor()
            node = ("binary", op, node, rhs)
        return node

    def _parse_factor(self) -> tuple[str, Any]:
        if self._peek() in {"+", "-"}:
            op = self._next()
            operand = self._parse_factor()
            return ("unary", op, operand)

        if self._peek() == "(":
            self._next()
            node = self._parse_expression()
            self._expect(")")
            return node

        if self._peek() is None:
            raise ParserError("Unexpected end of expression")

        if self._is_number_start(self._peek()):
            number = self._consume_number()
            return ("number", float(number))

        if self._is_identifier_start(self._peek()):
            name = self._consume_identifier()
            return ("name", name)

        raise ParserError(f"Unexpected token '{self._peek()}'")

    def _consume_number(self) -> str:
        start = self.index
        while self.index < len(self.source) and self.source[self.index].isdigit():
            self.index += 1
        if self.index < len(self.source) and self.source[self.index] == ".":
            self.index += 1
            while self.index < len(self.source) and self.source[self.index].isdigit():
                self.index += 1
        return self.source[start:self.index]

    def _consume_identifier(self) -> str:
        start = self.index
        if self.index < len(self.source) and (self.source[self.index].isalpha() or self.source[self.index] == "_"):
            self.index += 1
        while self.index < len(self.source) and (self.source[self.index].isalnum() or self.source[self.index] == "_"):
            self.index += 1
        return self.source[start:self.index]

    def _eval(self, node: tuple[str, Any], registers: RegisterStore | dict[str, float]) -> float:
        kind = node[0]
        if kind == "number":
            return float(node[1])
        if kind == "name":
            name = node[1]
            if isinstance(registers, RegisterStore):
                return registers.require(name)
            if name not in registers:
                raise KeyError(f"Register '{name}' is not defined")
            return float(registers[name])
        if kind == "unary":
            operator, operand = node[1], node[2]
            value = self._eval(operand, registers)
            return value if operator == "+" else -value
        if kind == "binary":
            operator, left, right = node[1], node[2], node[3]
            left_value = self._eval(left, registers)
            right_value = self._eval(right, registers)
            if operator == "+":
                return left_value + right_value
            if operator == "-":
                return left_value - right_value
            if operator == "*":
                return left_value * right_value
            if operator == "/":
                if right_value == 0:
                    raise ZeroDivisionError("Division by zero")
                return left_value / right_value
            raise ParserError(f"Unsupported operator: {operator}")

        raise ParserError(f"Unknown AST node: {kind}")

    def _peek(self) -> str | None:
        while self.index < len(self.source) and self.source[self.index].isspace():
            self.index += 1
        if self.index >= len(self.source):
            return None
        return self.source[self.index]

    def _next(self) -> str:
        while self.index < len(self.source) and self.source[self.index].isspace():
            self.index += 1
        if self.index >= len(self.source):
            raise ParserError("Unexpected end of expression")
        ch = self.source[self.index]
        self.index += 1
        return ch

    def _expect(self, token: str) -> None:
        actual = self._next()
        if actual != token:
            raise ParserError(f"Expected '{token}', found '{actual}'")

    @staticmethod
    def _is_number_start(ch: str | None) -> bool:
        return ch is not None and (ch.isdigit() or ch == ".")

    @staticmethod
    def _is_identifier_start(ch: str | None) -> bool:
        return ch is not None and (ch.isalpha() or ch == "_")


def evaluate_expression(expression: str, registers: RegisterStore | dict[str, float] | None = None, *, result_name: str | None = None) -> float:
    store = registers if isinstance(registers, RegisterStore) else RegisterStore.from_mapping(registers)
    result = ExpressionParser(expression).evaluate(store)
    if result_name is not None and isinstance(store, RegisterStore):
        store.set(result_name, result)
    return result
