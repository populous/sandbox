> **이전 안내 (2026-10-12)**
> 이 저장소의 내용은 비공개 저장소 `populous/pplx-sandbox`로 통합되었습니다.
> - `grammar/`, `src/`, `tests/test_parser.py`, `.devcontainer/`는 커밋 이력째 이전되었습니다.
> - Windows runner(`sandbox-run`), Thread Sync Protocol, 쓰레드 `thread/f7bfd4da` 기록은 pplx-sandbox에서 계속 관리합니다.
> - 이 저장소는 쓰기 가능한 상태로 유지되지만 새 작업은 pplx-sandbox에서 진행합니다.

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

## Testing

```bash
pytest
```

## User sandbox

Self-hosted runner 기반 사용자 정의 sandbox는 [docs/USER_SANDBOX.md](docs/USER_SANDBOX.md)를 참고하세요.

## Thread Sync Protocol

Perplexity 쓰레드 ↔ git 브랜치 동기화 규약은 [docs/THREAD_SYNC_PROTOCOL.md](docs/THREAD_SYNC_PROTOCOL.md), 도구는 `tools/pplx_thread.py`입니다.
