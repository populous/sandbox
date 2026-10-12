# User Sandbox (self-hosted runner)

Perplexity의 기본 sandbox를 대체하는 **사용자 정의 sandbox**입니다.
명령은 사용자가 소유한 WSL2/Linux 머신(self-hosted runner)에서 실행되고,
결과는 GitHub Actions 로그·artifact·sha256 manifest로 남습니다.

```
Perplexity ──(gh: branch/commit/PR, workflow run)──► populous/sandbox
                                                      │ workflow_dispatch: sandbox-run
                                                      ▼
                                 self-hosted runner [self-hosted, linux, user-sandbox]
                                 (사용자 WSL2 / 로컬 PC — 사용자가 직접 접근 가능)
                                                      │
                                                      ▼
                               run.log · command.sh · artifacts/ · manifest.json
```

## 1. Runner 설치 (WSL2 Ubuntu, 1회)

```bash
sudo apt-get update && sudo apt-get install -y curl tar python3 gh
gh auth login            # repo admin 권한 계정
git clone https://github.com/populous/sandbox && cd sandbox
bash scripts/runner/setup-runner.sh            # 대화형 실행: ~/actions-runner-user-sandbox/run.sh
# 또는 서비스로 상시 실행 (WSL2에서 systemd 필요)
bash scripts/runner/setup-runner.sh --service
```

WSL2 systemd 활성화: `/etc/wsl.conf`

```ini
[boot]
systemd=true
```

PowerShell에서 `wsl --shutdown` 후 재시작합니다.

확인:

```bash
gh api repos/populous/sandbox/actions/runners --jq '.runners[] | {name,status,labels:[.labels[].name]}'
```

제거: `bash scripts/runner/remove-runner.sh`

## 2. 실행

```bash
gh workflow run sandbox-run --repo populous/sandbox --ref main \
  -f command='python -m pytest -q' -f run_label='smoke'
gh run list --repo populous/sandbox --workflow sandbox-run -L 3
gh run watch <run-id> --repo populous/sandbox
gh run download <run-id> --repo populous/sandbox -D ./out
```

명령 안에서 `$SANDBOX_ARTIFACTS`에 쓴 파일은 artifact로 업로드되고 manifest에 sha256이 기록됩니다.

```bash
-f command='python -m arithmetic_registers "a+b*2" --register a=10 --register b=3 > $SANDBOX_ARTIFACTS/result.txt'
```

## 3. Perplexity 요청 템플릿

```text
populous/sandbox에서 sandbox-run을 ref=<branch>로 실행해줘.
command: <명령>
run_label: <라벨>
완료되면 manifest.json의 exit_code와 artifact 목록을 요약해줘.
```

## 4. 보안 (공개 저장소)

공개 저장소의 self-hosted runner는 외부인이 PR로 사용자 PC에서 코드를 실행할 위험이 있습니다. 이 구성은 다음으로 차단합니다.

- `sandbox-run`은 `workflow_dispatch` 전용 — push/pull_request 트리거 없음
- 작업은 `github.actor == github.repository_owner`일 때만 실행
- `ci.yml`은 GitHub-hosted `ubuntu-latest`만 사용 (self-hosted 라벨 금지)
- `permissions: contents: read`, `concurrency: user-sandbox`

추가 권장 설정 (Settings → Actions → General):

- Fork pull request workflows: **Require approval for all external contributors**
- 새 workflow에 `runs-on: self-hosted`를 쓰는 PR은 리뷰에서 거부
- runner는 전용 WSL2 배포판 또는 전용 사용자 계정에서 실행, 비밀키를 홈 디렉터리에 두지 않음

## 5. 파일

| 경로 | 역할 |
|---|---|
| `.github/workflows/sandbox-run.yml` | 수동 실행 workflow |
| `scripts/sandbox/run.sh` | 명령 실행, 로그, manifest 생성 |
| `scripts/runner/setup-runner.sh` | runner 등록/서비스 설치 |
| `scripts/runner/remove-runner.sh` | runner 해제 |
