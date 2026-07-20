"""Small, dependency-free parser for the Pinscape Pico configuration format.

Pinscape configurations are JavaScript-object-style files rather than strict
JSON: property names can be unquoted, comments are allowed, hexadecimal values
are common, and trailing commas are accepted.  This parser reads that subset
without evaluating code.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any


@dataclass
class Token:
    kind: str
    value: Any
    line: int
    column: int


class PinscapeParseError(ValueError):
    def __init__(self, message: str, line: int, column: int):
        super().__init__(f"Line {line}, column {column}: {message}")
        self.message = message
        self.line = line
        self.column = column


class Lexer:
    def __init__(self, text: str):
        self.text = text
        self.pos = 0
        self.line = 1
        self.column = 1

    def _advance(self, count: int = 1) -> str:
        chunk = self.text[self.pos:self.pos + count]
        self.pos += count
        for char in chunk:
            if char == "\n":
                self.line += 1
                self.column = 1
            else:
                self.column += 1
        return chunk

    def _skip_space_and_comments(self) -> None:
        while self.pos < len(self.text):
            if self.text[self.pos].isspace():
                self._advance()
            elif self.text.startswith("//", self.pos):
                while self.pos < len(self.text) and self.text[self.pos] != "\n":
                    self._advance()
            elif self.text.startswith("/*", self.pos):
                start_line, start_col = self.line, self.column
                self._advance(2)
                while self.pos < len(self.text) and not self.text.startswith("*/", self.pos):
                    self._advance()
                if self.pos >= len(self.text):
                    raise PinscapeParseError("Unterminated block comment", start_line, start_col)
                self._advance(2)
            else:
                return

    def next(self) -> Token:
        self._skip_space_and_comments()
        if self.pos >= len(self.text):
            return Token("EOF", None, self.line, self.column)

        line, column = self.line, self.column
        char = self.text[self.pos]
        if char in "{}[]:,":
            self._advance()
            return Token(char, char, line, column)

        if char in "\"'":
            quote = self._advance()
            value = []
            escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f"}
            while self.pos < len(self.text):
                char = self._advance()
                if char == quote:
                    return Token("STRING", "".join(value), line, column)
                if char == "\\":
                    if self.pos >= len(self.text):
                        break
                    escaped = self._advance()
                    value.append(escapes.get(escaped, escaped))
                else:
                    value.append(char)
            raise PinscapeParseError("Unterminated string", line, column)

        number = re.match(r"-?(?:0[xX][0-9a-fA-F]+|(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?)", self.text[self.pos:])
        if number:
            raw = number.group(0)
            self._advance(len(raw))
            if raw.lower().lstrip("-").startswith("0x"):
                sign = -1 if raw.startswith("-") else 1
                return Token("NUMBER", sign * int(raw.lstrip("-")[2:], 16), line, column)
            return Token("NUMBER", float(raw) if any(c in raw for c in ".eE") else int(raw), line, column)

        identifier = re.match(r"[A-Za-z_$][A-Za-z0-9_$-]*", self.text[self.pos:])
        if identifier:
            raw = identifier.group(0)
            self._advance(len(raw))
            values = {"true": True, "false": False, "null": None}
            if raw in values:
                return Token("LITERAL", values[raw], line, column)
            return Token("IDENT", raw, line, column)

        raise PinscapeParseError(f"Unexpected character {char!r}", line, column)


class Parser:
    def __init__(self, text: str):
        self.lexer = Lexer(text)
        self.current = self.lexer.next()

    def _take(self, kind: str) -> Token:
        if self.current.kind != kind:
            raise PinscapeParseError(
                f"Expected {kind!r}, found {self.current.kind!r}",
                self.current.line,
                self.current.column,
            )
        token = self.current
        self.current = self.lexer.next()
        return token

    def parse(self) -> Any:
        value = self._value()
        if self.current.kind != "EOF":
            raise PinscapeParseError("Unexpected content after configuration", self.current.line, self.current.column)
        return value

    def _value(self) -> Any:
        if self.current.kind == "{":
            return self._object()
        if self.current.kind == "[":
            return self._array()
        if self.current.kind in ("STRING", "NUMBER", "LITERAL"):
            token = self.current
            self.current = self.lexer.next()
            return token.value
        raise PinscapeParseError("Expected a value", self.current.line, self.current.column)

    def _object(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        self._take("{")
        while self.current.kind != "}":
            if self.current.kind not in ("STRING", "IDENT"):
                raise PinscapeParseError("Expected a property name", self.current.line, self.current.column)
            key = str(self.current.value)
            self.current = self.lexer.next()
            self._take(":")
            result[key] = self._value()
            if self.current.kind == ",":
                self._take(",")
                if self.current.kind == "}":
                    break
            elif self.current.kind != "}":
                raise PinscapeParseError("Expected ',' between properties", self.current.line, self.current.column)
        self._take("}")
        return result

    def _array(self) -> list[Any]:
        result: list[Any] = []
        self._take("[")
        while self.current.kind != "]":
            result.append(self._value())
            if self.current.kind == ",":
                self._take(",")
                if self.current.kind == "]":
                    break
            elif self.current.kind != "]":
                raise PinscapeParseError("Expected ',' between array items", self.current.line, self.current.column)
        self._take("]")
        return result


def loads(text: str) -> Any:
    return Parser(text.lstrip("\ufeff")).parse()
