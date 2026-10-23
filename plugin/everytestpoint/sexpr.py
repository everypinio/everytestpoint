"""Small, deterministic KiCad S-expression reader.

Only selected root forms are materialized. This keeps memory use predictable for boards that
contain large embedded images or fonts.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator


class SExprError(ValueError):
    pass


def tokenize(source: str) -> Iterator[str]:
    index = 0
    length = len(source)
    while index < length:
        char = source[index]
        if char.isspace():
            index += 1
            continue
        if char == ";":
            newline = source.find("\n", index + 1)
            index = length if newline < 0 else newline + 1
            continue
        if char in "()":
            yield char
            index += 1
            continue
        if char == '"':
            index += 1
            value: list[str] = []
            while index < length:
                char = source[index]
                if char == '"':
                    index += 1
                    break
                if char == "\\":
                    index += 1
                    if index >= length:
                        raise SExprError("unterminated escape in quoted string")
                    escaped = source[index]
                    value.append({"n": "\n", "r": "\r", "t": "\t"}.get(escaped, escaped))
                    index += 1
                    continue
                value.append(char)
                index += 1
            else:
                raise SExprError("unterminated quoted string")
            yield "".join(value)
            continue

        end = index
        while end < length and not source[end].isspace() and source[end] not in "()":
            end += 1
        yield source[index:end]
        index = end


class TokenStream:
    def __init__(self, tokens: Iterable[str]):
        self._tokens = iter(tokens)
        self._buffer: str | None = None

    def pop(self) -> str:
        if self._buffer is not None:
            value = self._buffer
            self._buffer = None
            return value
        try:
            return next(self._tokens)
        except StopIteration as exc:
            raise SExprError("unexpected end of S-expression") from exc

    def peek(self) -> str:
        if self._buffer is None:
            self._buffer = self.pop()
        return self._buffer


def _parse_after_open(stream: TokenStream, head: str) -> list:
    result: list = [head]
    while True:
        token = stream.pop()
        if token == ")":
            return result
        if token == "(":
            nested_head = stream.pop()
            if nested_head in "()":
                raise SExprError("list has no head atom")
            result.append(_parse_after_open(stream, nested_head))
        else:
            result.append(token)


def _skip_after_open(stream: TokenStream) -> None:
    depth = 1
    while depth:
        token = stream.pop()
        if token == "(":
            depth += 1
        elif token == ")":
            depth -= 1


def root_forms(source: str, keep: set[str], root_name: str = "kicad_pcb") -> Iterator[list]:
    """Yield selected direct children of a KiCad root S-expression."""

    stream = TokenStream(tokenize(source))
    if stream.pop() != "(" or stream.pop() != root_name:
        raise SExprError(f"expected a {root_name} root form")

    while True:
        token = stream.pop()
        if token == ")":
            return
        if token != "(":
            continue
        head = stream.pop()
        if head in keep:
            yield _parse_after_open(stream, head)
        else:
            _skip_after_open(stream)


def child(expr: list, name: str) -> list | None:
    return next((item for item in expr[1:] if isinstance(item, list) and item and item[0] == name), None)


def children(expr: list, name: str) -> list[list]:
    return [item for item in expr[1:] if isinstance(item, list) and item and item[0] == name]
