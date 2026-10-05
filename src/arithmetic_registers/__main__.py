from __future__ import annotations

import argparse

from .parser import evaluate_expression
from .registers import RegisterStore


def _parse_registers(raw: list[str]) -> RegisterStore:
    store = RegisterStore()
    for item in raw:
        if "=" not in item:
            raise ValueError(f"Register values must be in name=value format: {item!r}")
        name, value = item.split("=", 1)
        store.set(name.strip(), float(value.strip()))
    return store


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate arithmetic expressions using named registers.")
    parser.add_argument("expression")
    parser.add_argument("--register", dest="registers", action="append", default=[], help="Set a register using name=value")
    args = parser.parse_args()

    store = _parse_registers(args.registers)
    result = evaluate_expression(args.expression, store, result_name="result")
    print(result)


if __name__ == "__main__":
    main()
