# Contributing

## Language

All content in this repository is written in English: commit messages, code
comments, docstrings, documentation, issues, and pull requests.

## Workflow

1. Create a branch from `main` (`feat/`, `fix/`, `docs/`, `chore/`)
2. Write the failing test first, commit it as `test:`
3. Implement, commit as `feat:` or `fix:`
4. Run the same checks CI runs
5. Open a pull request and merge after CI passes

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy packages
uv run lint-imports
uv run pytest
```

## Commit messages

Conventional Commits.

| Prefix | Use |
|---|---|
| feat | New behaviour |
| fix | Bug fix |
| test | Tests only |
| refactor | No behaviour change |
| docs | Documentation |
| chore | Config, build, dependencies |

Commit tests separately from the implementation so the test-first history stays
visible.

## Architecture rules

The domain layer must not import external libraries, `pathlib`, `os`, or the
config module. These rules are enforced by import-linter and run in CI.
