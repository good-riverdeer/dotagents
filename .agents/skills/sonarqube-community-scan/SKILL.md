---
name: sonarqube-community-scan
description: Use when running static analysis with SonarQube Community Build (sonarqube:community image) — deploying the server with podman, scanning a repository, or reading issues and quality gate results through the sonar CLI.
---

# SonarQube Community Build scan

Server runs in podman; the **scan** is done by the `sonar-scanner-cli` container (no local Java needed); **results** are read with the `sonar` CLI.

`sonar analyze` / `analyze agentic` (Vortex) need a SonarQube Cloud/Server edition with that feature. On Community it only does local secrets scanning. Don't use it for project analysis.

## 1. Deploy server (once)

```bash
podman run -d --name sonarqube -p 9000:9000 \
  -v sonarqube_data:/opt/sonarqube/data -v sonarqube_extensions:/opt/sonarqube/extensions \
  -v sonarqube_logs:/opt/sonarqube/logs docker.io/library/sonarqube:community
until curl -s localhost:9000/api/system/status | grep -q '"UP"'; do sleep 5; done   # ~1-2 min
```
Already exists? `podman start sonarqube`. Port 9000 busy → change the host side and every URL below.

## 2. Credentials (first run)

```bash
# default admin:admin — change it
curl -u admin:admin -X POST localhost:9000/api/users/change_password -d login=admin -d previousPassword=admin -d password='<new>'
# two tokens: scanner uploads need an analysis token, CLI reads need a USER token
curl -u admin:'<new>' -X POST localhost:9000/api/user_tokens/generate -d name=scan -d type=GLOBAL_ANALYSIS_TOKEN
curl -u admin:'<new>' -X POST localhost:9000/api/user_tokens/generate -d name=cli  -d type=USER_TOKEN
echo "<user token>" | sonar auth login -s http://localhost:9000 --with-token
curl -u admin:'<new>' -X POST localhost:9000/api/projects/create -d project=<key> -d name=<key>
```
Never print tokens into the final answer or commit them. Pass the analysis token via `SONAR_TOKEN` env.

## 3. Scan (from the target repo root)

```bash
podman run --rm -e SONAR_HOST_URL=http://host.containers.internal:9000 -e SONAR_TOKEN="$SONAR_TOKEN" \
  -v "$PWD":/usr/src:Z docker.io/sonarsource/sonar-scanner-cli:latest \
  -Dsonar.projectKey=<key> -Dsonar.sources=<dirs,comma-separated> \
  -Dsonar.exclusions='**/tests/**,**/.venv/**'
```
Look for `EXECUTION SUCCESS`. Server processes the report asynchronously — wait a few seconds before reading results. A 100-file Python monorepo took ~3 min (mostly the JS/TS sensor warming up).

## 4. Read results

```bash
sonar list issues -p <key> --format table          # OPEN,CONFIRMED by default
sonar list issues -p <key> --severities HIGH,BLOCKER --new-code --format json
sonar qg status -p <key> [--all]                   # quality gate verdict
```

## Gotchas

| Symptom | Cause / fix |
|---|---|
| `qg status` → HTTP 403 | CLI logged in with the analysis token; re-login with a USER token |
| `Invalid severity CRITICAL` | Server is in MQR mode: use INFO, LOW, MEDIUM, HIGH, BLOCKER |
| `Unable to locate a Java Runtime` | Expected — use the scanner container, not a local scanner |
| `Authentication was not successful` / HTTPS warning from sonar-secrets | Harmless for plain-http localhost; secrets scan still runs |
| Scanner can't reach server | Use `host.containers.internal`, not `localhost`, inside the container |

Test target used while writing this skill: `~/workspace/agent-orchestrator/orchestrator` (project key `orchestrator`, Quality Gate passed, ~9 Python issues).
