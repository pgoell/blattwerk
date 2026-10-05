# blattwerk: project instructions

Worksheet tool for Grundschule teachers

## Layout

- `src/blattwerk/`: the package
- `tests/`: pytest

## Commands

mise owns every command. `mise tasks` lists them.

```sh
mise run test           # pytest
mise run lint           # ruff check, ruff format --check, ty check
mise run fmt            # ruff format
mise run check-commits  # cocogitto on unpushed commits
```

## Conventions

- Conventional Commits (`feat:`, `fix:`, `chore:` ...). The `commit-msg` hook rejects anything else.
- Default branch is `master`. With branch protection applied (`mise run repo:apply-settings`), changes land through PRs that pass Lint, Test and Commits.
- This project was generated from `gh:pgoell/project-template`. Update with `uvx copier update`.
