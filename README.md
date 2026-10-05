# blattwerk

Worksheet tool for Grundschule teachers

## Setup

Needs [mise](https://mise.jdx.dev).

```sh
mise install      # python, uv, lefthook, cocogitto, jq
mise run install  # git hooks + dependencies
mise run test
mise run lint     # ruff + ty
```

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org); the `commit-msg` hook checks them with cocogitto.

## Interview form

`/i/<token>` serves a German questionnaire with voice notes. Each submission lands in its own folder (`answers.json`, `audio-N.*`) under `BLATTWERK_DATA_DIR`. Any other path, or any wrong token, is a 404.

Deployed on the VPS at `blattwerk.pgoell.com`:

```sh
docker compose up -d --build
```

The token is in `~/.config/blattwerk/env` (`BLATTWERK_TOKEN=...`), and submissions land in `~/.local/share/blattwerk/`. Neither is in the repo.
