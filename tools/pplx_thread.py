#!/usr/bin/env python3
"""pplx-thread: Thread Sync Protocol (TSP) v1.

Binds one Perplexity thread to one git branch on GitHub origin so that the
Perplexity sandbox state (context, runs, artifacts) is reproducible and
accessible to the user from any local clone.

    branch  : thread/<short-id>
    folder  : threads/<short-id>/
    origin  : the GitHub remote of the checkout (default "origin")

Subcommands
    init        create or attach the thread branch and folder
    pull        sync from origin (rebase), picking up user changes
    run         execute a command, record log + sha256 manifest
    note        append a context note
    checkpoint  secret/size guard, commit with trailers, pull --rebase, push
    status      branch, ahead/behind, recent journal events
    close       mark thread closed and checkpoint

Stdlib only. Works on Linux (Perplexity sandbox), macOS, Windows.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import platform
import re
import shlex
import subprocess
import sys
from pathlib import Path

PROTOCOL = "pplx-thread/1"
MAX_FILE_BYTES = 5 * 1024 * 1024
SECRET_PATTERNS = [
    re.compile(rb"gh[pousr]_[A-Za-z0-9]{36,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{40,}"),
    re.compile(rb"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
    re.compile(rb"xox[abprs]-[A-Za-z0-9-]{10,}"),
    re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----"),
]


# ---------------------------------------------------------------- helpers
def now() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def git(repo: Path, *args: str, check: bool = True, capture: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], text=True,
                       capture_output=capture)
    if check and r.returncode != 0:
        sys.exit(f"git {' '.join(args)} failed:\n{r.stderr or r.stdout}")
    return (r.stdout or "").strip()


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Thread:
    def __init__(self, repo: Path, tid: str | None, remote: str):
        self.repo = repo.resolve()
        self.remote = remote
        self.tid = tid or self._detect()
        if not re.fullmatch(r"[A-Za-z0-9._-]{4,64}", self.tid):
            sys.exit(f"invalid thread id: {self.tid}")
        self.branch = f"thread/{self.tid}"
        self.dir = self.repo / "threads" / self.tid
        self.rel = f"threads/{self.tid}"

    def _detect(self) -> str:
        env = os.environ.get("PPLX_THREAD_ID")
        if env:
            return env
        b = git(Path(self_repo_hint()), "branch", "--show-current", check=False)
        if b.startswith("thread/"):
            return b.split("/", 1)[1]
        sys.exit("thread id unknown: pass --id or set PPLX_THREAD_ID")

    def journal(self, event: str, **data) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        rec = {"ts": now(), "event": event, "actor": actor(), **data}
        with (self.dir / "journal.jsonl").open("a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")


_REPO_HINT = "."


def self_repo_hint() -> str:
    return _REPO_HINT


def actor() -> str:
    return os.environ.get("PPLX_ACTOR") or ("perplexity" if Path("/home/user/workspace").exists() else "user")


# ---------------------------------------------------------------- commands
def cmd_init(t: Thread, a) -> None:
    git(t.repo, "fetch", t.remote, "--prune")
    remote_ref = f"{t.remote}/{t.branch}"
    has_remote = git(t.repo, "rev-parse", "--verify", "-q", remote_ref, check=False)
    has_local = git(t.repo, "rev-parse", "--verify", "-q", t.branch, check=False)
    if has_local:
        git(t.repo, "switch", t.branch)
    elif has_remote:
        git(t.repo, "switch", "-c", t.branch, "--track", remote_ref)
    else:
        git(t.repo, "switch", "-c", t.branch, f"{t.remote}/{a.base}")
    if has_remote:
        git(t.repo, "pull", "--rebase", t.remote, t.branch)

    t.dir.mkdir(parents=True, exist_ok=True)
    (t.dir / "context").mkdir(exist_ok=True)
    (t.dir / "runs").mkdir(exist_ok=True)
    meta = t.dir / "THREAD.json"
    if not meta.exists():
        meta.write_text(json.dumps({
            "protocol": PROTOCOL,
            "thread_id": t.tid,
            "thread_url": a.url,
            "title": a.title,
            "branch": t.branch,
            "base": a.base,
            "created_utc": now(),
            "status": "open",
        }, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        (t.dir / "README.md").write_text(
            f"# {a.title or t.tid}\n\n"
            f"- Thread: {a.url or '(unset)'}\n"
            f"- Branch: `{t.branch}`\n"
            f"- Protocol: `{PROTOCOL}` (see docs/THREAD_SYNC_PROTOCOL.md)\n\n"
            "| 폴더 | 내용 |\n|---|---|\n"
            "| `context/` | 결정·노트·요약 (사람과 Perplexity가 함께 편집) |\n"
            "| `runs/` | 실행 기록: command, log, outputs, manifest.json |\n"
            "| `journal.jsonl` | append-only 이벤트 로그 |\n",
            encoding="utf-8")
        for d in ("context", "runs"):
            (t.dir / d / ".gitkeep").touch()
        t.journal("init", base=a.base, url=a.url)
        _commit_push(t, f"init: {a.title or t.tid}")
    print(json.dumps({"branch": t.branch, "dir": t.rel, "remote_existed": bool(has_remote)}))


def cmd_pull(t: Thread, a) -> None:
    _ensure_branch(t)
    before = git(t.repo, "rev-parse", "HEAD")
    git(t.repo, "pull", "--rebase", "--autostash", t.remote, t.branch)
    after = git(t.repo, "rev-parse", "HEAD")
    changed = git(t.repo, "diff", "--name-only", before, after) if before != after else ""
    print(json.dumps({"updated": before != after, "files": changed.splitlines()}))


def cmd_run(t: Thread, a) -> None:
    _ensure_branch(t)
    label = re.sub(r"[^A-Za-z0-9._-]+", "-", a.label).strip("-") or "run"
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = t.dir / "runs" / f"{stamp}-{label}"
    (out / "outputs").mkdir(parents=True)
    command = a.command if isinstance(a.command, str) else shlex.join(a.command)
    (out / "command.txt").write_text(command + "\n", encoding="utf-8")
    env = {**os.environ, "PPLX_RUN_OUT": str(out / "outputs")}
    started = now()
    with (out / "run.log").open("w", encoding="utf-8") as log:
        p = subprocess.Popen(command, shell=True, cwd=t.repo / a.cwd, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                             text=True, encoding="utf-8", errors="replace")
        for line in p.stdout:
            sys.stdout.write(line)
            log.write(line)
        rc = p.wait()
    files = sorted(
        ({"path": f.relative_to(out).as_posix(), "sha256": sha256(f), "bytes": f.stat().st_size}
         for f in out.rglob("*") if f.is_file()),
        key=lambda x: x["path"])
    manifest = {
        "protocol": PROTOCOL, "thread_id": t.tid, "label": label,
        "command": command, "cwd": a.cwd, "exit_code": rc,
        "started_utc": started, "finished_utc": now(),
        "git_head": git(t.repo, "rev-parse", "HEAD"),
        "actor": actor(),
        "host": {"system": platform.system(), "release": platform.release(),
                 "machine": platform.machine(), "python": platform.python_version()},
        "files": files,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
                                       encoding="utf-8")
    t.journal("run", label=label, exit_code=rc, path=out.relative_to(t.repo).as_posix())
    print(json.dumps({"run": out.relative_to(t.repo).as_posix(), "exit_code": rc}))
    if a.checkpoint:
        _commit_push(t, f"run: {label} (exit {rc})")
    sys.exit(rc)


def cmd_note(t: Thread, a) -> None:
    _ensure_branch(t)
    f = t.dir / "context" / "notes.md"
    with f.open("a", encoding="utf-8") as fh:
        fh.write(f"\n## {now()} ({actor()})\n\n{a.text.strip()}\n")
    t.journal("note", chars=len(a.text))
    print(f.relative_to(t.repo).as_posix())


def cmd_checkpoint(t: Thread, a) -> None:
    _ensure_branch(t)
    _guard(t)
    t.journal("checkpoint", message=a.message)
    _commit_push(t, f"checkpoint: {a.message}")


def cmd_status(t: Thread, a) -> None:
    git(t.repo, "fetch", t.remote, check=False)
    cur = git(t.repo, "branch", "--show-current")
    ab = git(t.repo, "rev-list", "--left-right", "--count", f"{t.remote}/{t.branch}...HEAD", check=False)
    behind, ahead = (ab.split() + ["?", "?"])[:2]
    events = []
    j = t.dir / "journal.jsonl"
    if j.exists():
        events = [json.loads(x) for x in j.read_text(encoding="utf-8").splitlines()[-a.n:]]
    print(json.dumps({"branch": cur, "expected": t.branch, "ahead": ahead, "behind": behind,
                      "dirty": bool(git(t.repo, "status", "--porcelain", "--", t.rel)),
                      "recent": events}, indent=2, ensure_ascii=False))


def cmd_close(t: Thread, a) -> None:
    _ensure_branch(t)
    meta = t.dir / "THREAD.json"
    d = json.loads(meta.read_text(encoding="utf-8"))
    d.update(status="closed", closed_utc=now(), summary=a.summary)
    meta.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    t.journal("close", summary=a.summary)
    _commit_push(t, "close")


# ---------------------------------------------------------------- internals
def _ensure_branch(t: Thread) -> None:
    cur = git(t.repo, "branch", "--show-current")
    if cur != t.branch:
        sys.exit(f"on '{cur}', expected '{t.branch}'. run: pplx_thread.py init --id {t.tid}")


def _guard(t: Thread) -> None:
    out = git(t.repo, "status", "--porcelain", "-uall", "--", t.rel)
    bad = []
    for line in out.splitlines():
        path = line[3:].split(" -> ")[-1].strip('"')
        p = t.repo / path
        if not p.is_file():
            continue
        if p.stat().st_size > MAX_FILE_BYTES:
            bad.append(f"too large (> {MAX_FILE_BYTES} bytes): {path}")
            continue
        blob = p.read_bytes()
        for pat in SECRET_PATTERNS:
            if pat.search(blob):
                bad.append(f"possible secret ({pat.pattern[:20]!r}): {path}")
                break
    if bad:
        sys.exit("checkpoint blocked:\n  " + "\n  ".join(bad))


def _commit_push(t: Thread, summary: str) -> None:
    _guard(t)
    git(t.repo, "add", "--", t.rel)
    if not git(t.repo, "diff", "--cached", "--name-only"):
        print("nothing to commit")
    else:
        meta = json.loads((t.dir / "THREAD.json").read_text(encoding="utf-8"))
        msg = (f"thread({t.tid}): {summary}\n\n"
               f"Thread-Id: {t.tid}\n"
               f"Thread-URL: {meta.get('thread_url') or ''}\n"
               f"Protocol: {PROTOCOL}\n"
               f"Actor: {actor()}\n")
        git(t.repo, "commit", "-q", "-m", msg)
    has_remote = git(t.repo, "rev-parse", "--verify", "-q", f"{t.remote}/{t.branch}", check=False)
    if has_remote:
        git(t.repo, "pull", "--rebase", "--autostash", t.remote, t.branch)
    git(t.repo, "push", "-u", t.remote, t.branch)
    print(json.dumps({"pushed": t.branch, "head": git(t.repo, "rev-parse", "--short", "HEAD")}))


def main(argv=None) -> None:
    global _REPO_HINT
    ap = argparse.ArgumentParser(prog="pplx_thread", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--repo", default=".", help="git checkout (default: .)")
    ap.add_argument("--id", help="thread short id (default: $PPLX_THREAD_ID or current branch)")
    ap.add_argument("--remote", default="origin")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init"); s.add_argument("--url", default=""); s.add_argument("--title", default="")
    s.add_argument("--base", default="main")
    sub.add_parser("pull")
    s = sub.add_parser("run"); s.add_argument("--label", default="run"); s.add_argument("--cwd", default=".")
    s.add_argument("--checkpoint", action="store_true"); s.add_argument("command")
    s = sub.add_parser("note"); s.add_argument("text")
    s = sub.add_parser("checkpoint"); s.add_argument("-m", "--message", default="update")
    s = sub.add_parser("status"); s.add_argument("-n", type=int, default=5)
    s = sub.add_parser("close"); s.add_argument("--summary", default="")

    a = ap.parse_args(argv)
    _REPO_HINT = a.repo
    t = Thread(Path(a.repo), a.id, a.remote)
    {"init": cmd_init, "pull": cmd_pull, "run": cmd_run, "note": cmd_note,
     "checkpoint": cmd_checkpoint, "status": cmd_status, "close": cmd_close}[a.cmd](t, a)


if __name__ == "__main__":
    main()
