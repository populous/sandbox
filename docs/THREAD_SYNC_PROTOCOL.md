# Thread Sync Protocol (TSP) v1 — `pplx-thread/1`

Perplexity 쓰레드의 sandbox 상태를 **git 브랜치 1개 ↔ 쓰레드 1개**로 GitHub origin에 고정하여,
사용자가 로컬 git으로 그대로 접근·수정·재현할 수 있게 하는 규약입니다.

## 1. 역할과 신뢰 경계

```
┌──────────── Perplexity sandbox (쓰레드별, 임시) ────────────┐
│ /home/user/workspace/<repo>   ← git checkout                 │
│   python 내부연산 → tools/pplx_thread.py run                 │
│   context 기록   → note / checkpoint                         │
└───────────────┬──────────────────────────────────────────────┘
                │ git push / pull --rebase  (branch: thread/<id>)
                ▼
        GitHub origin: populous/sandbox      ← 단일 진실 원천(SSOT)
                ▲
                │ git fetch / switch / push
┌───────────────┴──────────────────────────────────────────────┐
│ 사용자 로컬 (Windows git / VS Code / Codespace)               │
└──────────────────────────────────────────────────────────────┘
```

- Perplexity sandbox는 **휘발성**입니다. 영속 상태는 origin의 `thread/<id>` 브랜치뿐입니다.
- 사용자는 sandbox 셸에 직접 들어가지 않습니다. 대신 **동일한 상태를 git으로 받습니다**.
- 사용자가 브랜치에 push한 변경은 Perplexity가 다음 턴 시작 시 `pull`로 받습니다.

## 2. 식별자

| 항목 | 규칙 | 예 |
|---|---|---|
| Thread ID | 쓰레드 UUID의 앞 8자 | `f7bfd4da` |
| Branch | `thread/<id>` | `thread/f7bfd4da` |
| Folder | `threads/<id>/` | `threads/f7bfd4da/` |
| Run ID | `<UTC yyyymmddTHHMMSSZ>-<label>` | `20261012T042607Z-calc` |

## 3. 폴더 구조

```
threads/<id>/
├── THREAD.json        # protocol, thread_url, title, base, status(open|closed)
├── README.md          # 사람용 안내
├── journal.jsonl      # append-only 이벤트 {ts, event, actor, ...}
├── context/           # 결정·노트·요약 (양측 편집 가능)
│   └── notes.md
└── runs/<run-id>/     # 실행 1회 = 폴더 1개 (불변)
    ├── command.txt
    ├── run.log
    ├── outputs/       # 명령이 $PPLX_RUN_OUT 에 쓴 파일
    └── manifest.json  # exit_code, git_head, host, files[{path,sha256,bytes}]
```

## 4. 연산 (Operations)

| Op | 시점 | 동작 |
|---|---|---|
| `init` | 쓰레드 첫 작업 | origin에 브랜치가 있으면 attach, 없으면 `base`에서 생성 → 폴더 생성 → push |
| `pull` | **매 턴 시작** | `pull --rebase --autostash` 로 사용자 변경 수신 |
| `run` | 내부연산마다 | 명령 실행, 로그·출력·manifest 기록 (`--checkpoint`로 즉시 push) |
| `note` | 결정/요약 발생 시 | `context/notes.md`에 타임스탬프와 actor로 추가 |
| `checkpoint` | **매 턴 종료** 또는 의미 있는 단위 | 가드 → commit(trailer) → pull --rebase → push |
| `status` | 수시 | 브랜치, ahead/behind, dirty, 최근 이벤트 |
| `close` | 쓰레드 종료 | `THREAD.json.status=closed` → checkpoint |

## 5. 커밋 규약

```
thread(<id>): <op>: <summary>

Thread-Id: <id>
Thread-URL: https://www.perplexity.ai/computer/tasks/<uuid>
Protocol: pplx-thread/1
Actor: perplexity | user
```

사용자 커밋은 자유 형식이어도 됩니다. 다만 `threads/<id>/` 밖을 건드리는 변경은 PR로 분리합니다.

## 6. 불변 규칙

1. `main`에는 push하지 않습니다. 쓰레드 결과의 `main` 반영은 PR로만 합니다.
2. Perplexity는 `threads/<id>/`만 stage합니다 (`git add -- threads/<id>`).
3. `runs/<run-id>/`는 생성 후 수정하지 않습니다 (재실행은 새 run).
4. `journal.jsonl`은 append-only입니다.
5. **checkpoint 가드**: 5 MB 초과 파일과 토큰 패턴(`ghp_`, `github_pat_`, `sk-`, `AKIA`, `xox*`, private key)이 있으면 커밋을 거부합니다.
6. 충돌 시 Perplexity는 force-push하지 않고, 사용자에게 보고한 뒤 멈춥니다.
7. 공개 저장소이므로 개인정보, 비밀키, 비공개 데이터는 `context/`에 쓰지 않습니다.

## 7. 턴 수명주기 (Perplexity 측)

```bash
REPO=/home/user/workspace/sandbox
T="python3 $REPO/tools/pplx_thread.py --repo $REPO --id <id>"
[ -d $REPO/.git ] || gh repo clone populous/sandbox $REPO
$T init --url <thread-url> --title "<title>"     # 이미 있으면 attach
$T pull                                           # 턴 시작
$T run --label <label> '<python 등 명령>'          # 내부연산
$T note "<결정/요약>"
$T checkpoint -m "<turn summary>"                 # 턴 종료
```

## 8. 사용자 측 접근

```powershell
git clone https://github.com/populous/sandbox
cd sandbox
git fetch origin
git switch thread/f7bfd4da          # 쓰레드 상태 그대로
git pull                            # Perplexity의 최신 checkpoint
# context/notes.md 수정, 파일 추가 후
git commit -am "user: <내용>" ; git push
```

- 웹: `https://github.com/populous/sandbox/tree/thread/<id>/threads/<id>`
- Codespace: 브랜치 `thread/<id>`로 생성
- 재실행: `python tools/pplx_thread.py --id <id> run --label repro '<command.txt 내용>'` 후 manifest의 sha256 비교

## 9. 쓰레드에서 쓰는 요청 문장

```text
이 쓰레드를 TSP로 populous/sandbox에 연결해줘. (init)
<연산>을 run으로 실행하고 checkpoint 해줘.
내가 thread/<id>에 push했어. pull하고 이어서 진행해줘.
쓰레드를 close하고 main 대상 PR을 만들어줘.
```
