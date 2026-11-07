# dotagents

개인 AI 코딩 에이전트(Claude Code, Codex 등) 설정의 정본(source of truth) 저장소입니다.
스킬, 공통 지침, Claude Code 프로젝트 설정을 한곳에서 관리합니다.

## 구성

| 경로 | 내용 |
|---|---|
| `.agents/AGENTS.md` | 모든 에이전트 공통 지침 |
| `.claude/CLAUDE.md` | `.agents/AGENTS.md`를 가리키는 symlink |
| `.agents/skills/<name>/` | 스킬 원본. 이 저장소에서 직접 관리하는 것과 외부에서 설치한 것이 섞여 있음 |
| `.claude/skills/<name>` | `.agents/skills/<name>`을 가리키는 상대 symlink (Claude Code가 읽는 위치) |
| `.claude/settings.json` | 프로젝트 공유 설정: 플러그인, marketplace, statusLine |
| `.claude/statusline.sh` | statusLine 스크립트 |
| `scripts/validate.py` | 스킬 frontmatter 등 구성 검증 (CI에서도 실행) |
| `.github/workflows/` | 검증과 외부 스킬 주간 업데이트 워크플로 |
| `skills-lock.json` | 외부에서 설치한 스킬의 출처와 해시 (`npx skills`가 관리) |

### 스킬 목록

| 스킬 | 관리 방식 |
|---|---|
| `git-branch-convention` | 직접 관리 |
| `sonarqube-community-scan` | 직접 관리 |
| `find-skills`, `frontend-slides`, `orca-cli`, `orca-computer-use`, `orchestration` | 외부 설치. `skills-lock.json`에 출처 기록 |

## 새 스킬 추가

1. `.agents/skills/<name>/SKILL.md`를 만든다. frontmatter에 `name`과 `description`이 필요하다.
2. Claude Code용 symlink를 만든다.
   ```bash
   ln -s ../../.agents/skills/<name> .claude/skills/<name>
   ```
3. 위 표에 한 줄 추가한다.

## 플러그인

`.claude/settings.json`의 `enabledPlugins`가 활성화할 플러그인을 선언하고, `extraKnownMarketplaces`가 기본 제공이 아닌 marketplace를 등록한다.
이 저장소를 연 Claude Code는 처음 실행할 때 marketplace 등록과 플러그인 설치를 안내한다. 수동으로 설치하려면:

```text
/plugin marketplace add DietrichGebert/ponytail          # ponytail marketplace (한 번만)
/plugin install superpowers@claude-plugins-official
/plugin install claude-md-management@claude-plugins-official
/plugin install ponytail@ponytail
```

`claude-plugins-official`은 Claude Code 기본 marketplace라서 별도 등록이 필요 없다.

### 설치 시점의 버전 기록

플러그인은 설정 파일로 버전을 고정할 수 없으므로 재현이 필요할 때 참고하도록 기록만 남긴다.
(`~/.claude/plugins/installed_plugins.json` 기준, 2026-11-07, ponytail은 같은 날 갱신)

| 플러그인 | 버전 | git commit |
|---|---|---|
| `superpowers@claude-plugins-official` | 7.0.0 | `bb92a77741419a4ab5f06e711a283343f1ada0c3` |
| `claude-md-management@claude-plugins-official` | 1.0.0 | `8deab8460a9d4df5a01315ef722a5ca6b061c074` |
| `ponytail@ponytail` | 5.3.3 | `96608e078b2d5ea607c5c3b8b5a54d1c1fba6846` |

특정 버전이 필요하면 marketplace를 clone한 뒤 해당 commit으로 checkout한 로컬 경로를 marketplace로 등록한다.

## statusLine

`.claude/settings.json`이 `.claude/statusline.sh`를 가리킨다. 출력 형식은 `➜ 디렉터리 git:(브랜치) ✗ [모델 컨텍스트%]`이며 `jq`가 필요하다.

이 설정은 이 저장소 안에서 실행한 세션에만 적용된다. 모든 프로젝트에서 쓰려면 글로벌 `~/.claude/settings.json`의 `statusLine.command`를 이 저장소의 스크립트 절대경로로 바꾼다.

## 업데이트 반영

### 외부 설치 스킬

```bash
npx skills update -p -y     # 최신 버전을 받고 skills-lock.json 해시를 갱신
git diff                    # 상류 변경 내용 검토 후 커밋
```

다른 머신에서 lock 기준 상태로 복원할 때는 `npx skills experimental_install`을 쓴다.
직접 만든 스킬(`git-branch-convention`, `sonarqube-community-scan`)은 lock 대상이 아니다.

### 플러그인

Claude Code에서 `/plugin update`를 실행한 뒤 아래 명령으로 현재 버전을 확인하고, 위 "설치 시점의 버전 기록" 표를 갱신한다.
(`everything-claude-code`는 이 저장소 대상이 아니므로 표에 넣지 않는다.)

```bash
jq -r '.plugins|to_entries[]|.key as $k|.value[]|"\($k) \(.version) \(.gitCommitSha)"' ~/.claude/plugins/installed_plugins.json
```

### GitHub Actions

| 워크플로 | 시점 | 동작 |
|---|---|---|
| `validate.yml` | push(main, develop), PR | `scripts/validate.py` 실행 |
| `update-skills.yml` | 매주 토요일 06:00 KST + 수동 | `npx skills update -p -y` 후 변경이 있으면 `chore/update-skills` PR 생성 |

`validate.py`가 검사하는 것: 스킬 frontmatter(`name`이 디렉터리명과 일치, `description` 존재 및 1024자 이하), `.claude/skills` symlink의 존재와 유효성, JSON 파일 형식, `skills-lock.json`과 디렉터리 일치, SonarQube 토큰 유출.
로컬에서는 `uv run --with pyyaml scripts/validate.py`로 실행한다.

`update-skills.yml`이 PR을 만들려면 저장소 설정(Settings → Actions → General)에서 "Allow GitHub Actions to create and approve pull requests"를 켜야 한다.
플러그인은 설정 파일로 고정·자동 갱신할 수 없어서 워크플로 대상이 아니다.

## 이 저장소를 글로벌에서 쓰기

원격에서 clone한 머신에서 글로벌 스킬과 지침을 이 저장소로 연결하려면 symlink를 직접 건다. 기존 파일이 있으면 먼저 백업한다.

```bash
REPO=~/workspace/dotagents
ln -s $REPO/.agents/AGENTS.md ~/.agents/AGENTS.md              # ~/.claude/CLAUDE.md, ~/.codex/AGENTS.md가 이 파일을 가리킴
ln -s $REPO/.agents/skills/<name> ~/.agents/skills/<name>
ln -s ../../.agents/skills/<name> ~/.claude/skills/<name>
```
