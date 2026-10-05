import pytest

from arithmetic_registers import RegisterStore, evaluate_expression


def test_register_evaluation():
    store = RegisterStore({"a": 10, "b": 3})
    assert evaluate_expression("a + b * 2", store) == 16.0


def test_parenthesized_expression():
    store = RegisterStore({"a": 4, "b": 2})
    assert evaluate_expression("(a + b) * 3", store) == 18.0


def test_unary_and_division():
    store = RegisterStore({"a": 8, "b": 2})
    assert evaluate_expression("-(a / b) + 5", store) == 1.0


def test_unknown_register_raises():
    with pytest.raises(KeyError):
        evaluate_expression("a + 1", {"b": 2})


def test_invalid_expression_raises():
    with pytest.raises(ValueError):
        evaluate_expression("2 + * 3")
