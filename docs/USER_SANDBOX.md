# User Sandbox (Windows self-hosted runner)

Perplexity의 기본 sandbox를 대체하는 **사용자 정의 sandbox**입니다.
명령은 사용자가 소유한 Windows PC(self-hosted runner)에서 PowerShell로 실행되고,
결과는 GitHub Actions 로그·artifact·sha256 manifest로 남습니다.

```
Perplexity ──(gh: branch/commit/PR, workflow run)──► populous/sandbox
                                                      │ workflow_dispatch: sandbox-run
                                                      ▼
                          self-hosted runner [self-hosted, windows, user-sandbox]
                          (사용자 Windows PC — 사용자가 직접 접근 가능)
                                                      │
                                                      ▼
                        run.log · command.ps1 · artifacts\ · manifest.json
```

## 1. 사전 설치 (1회)

PowerShell에서:

```powershell
winget install --id Git.Git -e
winget install --id GitHub.cli -e
winget install --id Python.Python.3.12 -e     # Python 작업을 실행할 경우
```

설치 후 PowerShell 창을 새로 열고 로그인합니다.

```powershell
gh auth login      # GitHub.com → HTTPS → 브라우저 로그인 (repo admin 계정)
```

## 2. Runner 등록

```powershell
cd $HOME
git clone https://github.com/populous/sandbox
cd sandbox
powershell -ExecutionPolicy Bypass -File scripts\runner\setup-runner.ps1
cd C:\actions-runner-user-sandbox ; .\run.cmd      # 창을 열어 두면 대기 상태
```

PC 부팅 시 자동 실행하려면 **관리자 PowerShell**에서:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\runner\setup-runner.ps1 -Service
Get-Service actions.runner.*
```

서비스 모드는 기본적으로 `NETWORK SERVICE` 계정으로 실행되므로, 사용자 계정에만 설치된 Python 등이 보이지 않을 수 있습니다. 이 경우 대화형 `run.cmd` 모드를 쓰거나 도구를 시스템 전체(All users)로 설치합니다.

확인:

```powershell
gh api repos/populous/sandbox/actions/runners --jq '.runners[] | {name,status,labels:[.labels[].name]}'
```

제거: `powershell -ExecutionPolicy Bypass -File scripts\runner\remove-runner.ps1`

## 3. 실행

`command`는 **PowerShell** 문법입니다.

```powershell
gh workflow run sandbox-run --repo populous/sandbox --ref main `
  -f command='python -m pip install -e . pytest; python -m pytest -q' -f run_label='smoke'
gh run list --repo populous/sandbox --workflow sandbox-run -L 3
gh run watch <run-id> --repo populous/sandbox
gh run download <run-id> --repo populous/sandbox -D .\out
```

명령 안에서 `$env:SANDBOX_ARTIFACTS`에 쓴 파일은 artifact로 업로드되고 manifest에 sha256이 기록됩니다.

```powershell
-f command='python -m arithmetic_registers "a+b*2" --register a=10 --register b=3 | Set-Content "$env:SANDBOX_ARTIFACTS\result.txt"'
```

종료 코드 규칙:

| 상황 | exit_code |
|---|---|
| 정상 | 0 |
| 마지막 네이티브 명령 실패 | 해당 `$LASTEXITCODE` |
| PowerShell 예외(`throw`, cmdlet 오류) | 1 |
| 잘못된 workdir (`..`, 절대경로) | 2 |

중간 네이티브 명령의 실패까지 잡으려면 `cmd; if ($LASTEXITCODE) { exit $LASTEXITCODE }` 형태로 이어 씁니다.

## 4. Perplexity 요청 템플릿

```text
populous/sandbox에서 sandbox-run을 ref=<branch>로 실행해줘.
command: <PowerShell 명령>
run_label: <라벨>
완료되면 manifest.json의 exit_code와 artifact 목록을 요약해줘.
```

## 5. 보안 (공개 저장소)

공개 저장소의 self-hosted runner는 외부인이 PR로 사용자 PC에서 코드를 실행할 위험이 있습니다. 이 구성은 다음으로 차단합니다.

- `sandbox-run`은 `workflow_dispatch` 전용 — push/pull_request 트리거 없음
- 작업은 `github.actor == github.repository_owner`일 때만 실행
- `ci.yml`은 GitHub-hosted `ubuntu-latest`만 사용 (self-hosted 라벨 금지)
- `permissions: contents: read`, `concurrency: user-sandbox`

추가 권장 설정 (Settings → Actions → General):

- Fork pull request workflows: **Require approval for all external contributors**
- 새 workflow에 `runs-on: self-hosted`를 쓰는 PR은 리뷰에서 거부
- runner 폴더(`C:\actions-runner-user-sandbox`)에 비밀키나 개인 파일을 두지 않음

## 6. 파일

| 경로 | 역할 |
|---|---|
| `.github/workflows/sandbox-run.yml` | 수동 실행 workflow (Windows, PowerShell) |
| `scripts/sandbox/run.ps1` | 명령 실행, 로그, manifest 생성 (PS 5.1 / 7 호환) |
| `scripts/runner/setup-runner.ps1` | runner 등록 / `-Service` 서비스 설치 |
| `scripts/runner/remove-runner.ps1` | runner 해제 |
