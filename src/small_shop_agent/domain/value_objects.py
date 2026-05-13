"""Simple value objects for domain invariants."""
from __future__ import annotations


class Rating:
    """Rating value object — ensures 1-5 range."""
    __slots__ = ("_value",)

    def __init__(self, value: int) -> None:
        if not (1 <= value <= 5):
            raise ValueError(f"Rating must be 1-5, got {value}")
        self._value = value

    @property
    def value(self) -> int:
        return self._value

    def is_negative(self) -> bool:
        return self._value <= 2

    def is_neutral(self) -> bool:
        return self._value == 3

    def is_positive(self) -> bool:
        return self._value >= 4
