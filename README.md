# Arithmetic Grammar and Register Flow

This repository provides a compact arithmetic grammar using EBNF and ANTLR-style syntax while keeping runtime state in a register-driven flow. The goal is to preserve a clean grammar boundary and move value handling to named registers.

## What is included

- EBNF grammar for arithmetic expressions
- ANTLR-compatible `g4` grammar for the same language
- A lightweight Python parser and evaluator
- A register store for variable resolution
- CI automation for GitHub Actions
- A dev container setup for Codespaces and local development

## Supported operation model

The grammar focuses on syntax only:

- arithmetic operators: `+`, `-`, `*`, `/`
- unary signs: `+x`, `-x`
- parentheses: `(a + b)`
- identifiers and numeric literals

The execution layer resolves names from a register store instead of embedding runtime behavior directly into the grammar.

## Local usage

```bash
python -m arithmetic_registers "a + b * 2" --register a=10 --register b=3
```

This prints:

```text
16.0
```

## Grammar files

- `grammar/Arithmetic.ebnf`
- `grammar/Arithmetic.g4`

## Environment coverage

The repository is structured to run across the full development path:

- sandbox
- local workstation
- remote checkout
- GitHub Codespaces
- GitHub Actions

## CMake and CTest workflow

This project is now configured as a Python-first CMake project. The test suite is wrapped through CTest, so the project can be executed in local, remote, Codespaces, and GitHub Actions environments with the same entry points.

```bash
cmake -S . -B build
cmake --build build
ctest --test-dir build -C Debug --output-on-failure
```

Additional project options can be customized from CMake:

```bash
cmake -S . -B build \
  -DARITHMETIC_ENABLE_GENERAL=ON \
  -DARITHMETIC_ENABLE_TEST=ON \
  -DARITHMETIC_ENABLE_DOC=ON \
  -DARITHMETIC_ENABLE_PACT=ON \
  -DARITHMETIC_ENABLE_PROFILING=ON
```

The CTest layer wraps the pytest suite by invoking:

```bash
python -m pytest -q tests
```

A presets file is also included for a default CMake build configuration:

```bash
cmake --preset default
cmake --build --preset default
ctest --preset default
```
