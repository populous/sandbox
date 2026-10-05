from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


@dataclass
class RegisterStore:
    values: dict[str, float] = field(default_factory=dict)

    def set(self, name: str, value: float) -> None:
        self.values[name] = float(value)

    def get(self, name: str, default: float | None = None) -> float | None:
        return self.values.get(name, default)

    def require(self, name: str) -> float:
        if name not in self.values:
            raise KeyError(f"Register '{name}' is not defined")
        return float(self.values[name])

    @classmethod
    def from_mapping(cls, values: Mapping[str, float] | None = None) -> "RegisterStore":
        store = cls()
        if values:
            for name, value in values.items():
                store.set(name, value)
        return store

    def clear(self) -> None:
        self.values.clear()
