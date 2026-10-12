#!/usr/bin/env bash
# Execute SANDBOX_COMMAND, capture log, and write a sha256 manifest.
# Inputs (env): SANDBOX_COMMAND, SANDBOX_WORKDIR (default "."),
#               SANDBOX_LABEL (default "manual"), SANDBOX_OUT (output dir).
# Outputs in $SANDBOX_OUT: run.log, manifest.json, and anything the command
# writes to $SANDBOX_ARTIFACTS (exported for the command).
set -uo pipefail

: "${SANDBOX_COMMAND:?SANDBOX_COMMAND is required}"
export SANDBOX_WORKDIR="${SANDBOX_WORKDIR:-.}"
export SANDBOX_LABEL="${SANDBOX_LABEL:-manual}"
SANDBOX_OUT="${SANDBOX_OUT:-$PWD/.sandbox-out}"

mkdir -p "$SANDBOX_OUT/artifacts"
export SANDBOX_ARTIFACTS="$SANDBOX_OUT/artifacts"

repo_root="$(pwd)"
case "$SANDBOX_WORKDIR" in
  /*|*..*) echo "workdir must be a relative path inside the repo" >&2; exit 2 ;;
esac
cd "$repo_root/$SANDBOX_WORKDIR" || { echo "workdir not found: $SANDBOX_WORKDIR" >&2; exit 2; }

started="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%s\n' "$SANDBOX_COMMAND" > "$SANDBOX_OUT/command.sh"

bash -o pipefail "$SANDBOX_OUT/command.sh" 2>&1 | tee "$SANDBOX_OUT/run.log"
rc=${PIPESTATUS[0]}
finished="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

cd "$SANDBOX_OUT"
python3 - "$rc" "$started" "$finished" <<'PY'
import hashlib, json, os, platform, sys
rc, started, finished = int(sys.argv[1]), sys.argv[2], sys.argv[3]
files = []
for root, _, names in os.walk("."):
    for n in sorted(names):
        p = os.path.relpath(os.path.join(root, n), ".")
        if p == "manifest.json":
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        files.append({"path": p, "sha256": h, "bytes": os.path.getsize(p)})
manifest = {
    "schema": "user-sandbox/manifest@1",
    "label": os.environ.get("SANDBOX_LABEL"),
    "command": os.environ.get("SANDBOX_COMMAND"),
    "workdir": os.environ.get("SANDBOX_WORKDIR", "."),
    "exit_code": rc,
    "started_utc": started,
    "finished_utc": finished,
    "git_sha": os.environ.get("GITHUB_SHA"),
    "git_ref": os.environ.get("GITHUB_REF"),
    "run_id": os.environ.get("GITHUB_RUN_ID"),
    "runner_name": os.environ.get("RUNNER_NAME"),
    "host": {"system": platform.system(), "release": platform.release(),
             "machine": platform.machine(), "python": platform.python_version()},
    "files": sorted(files, key=lambda f: f["path"]),
}
json.dump(manifest, open("manifest.json", "w"), indent=2)
print(json.dumps({"exit_code": rc, "files": len(files)}))
PY
exit "$rc"
