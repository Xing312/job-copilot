# Contributing

This project uses a pull-request workflow. The `main` branch is protected and
deploys to production (Render), so changes reach it only through a green PR.

## Workflow

1. **Branch off `main`:**

   ```bash
   git checkout main && git pull
   git checkout -b feat/short-description   # or fix/…, chore/…, docs/…
   ```

2. **Make your change and verify locally:**

   ```bash
   make test        # backend tests + extractor unit tests
   make start       # smoke-test the app at http://localhost:5173
   ```

3. **Open a pull request** against `main`. CI (`.github/workflows/ci.yml`) runs
   automatically:
   - **Frontend build** — `npm run build`
   - **Backend checks** — `ruff` lint, Alembic migrations on Postgres, `pytest`

4. **Merge once CI is green.** Branch protection blocks merging while checks are
   failing. Deployment to Render follows the merge.

## Branch naming

| Prefix | Use for |
|--------|---------|
| `feat/` | new features |
| `fix/` | bug fixes |
| `chore/` | tooling, deps, config |
| `docs/` | documentation only |

## Conventions

- Code comments and docstrings in English (`DEVLOG.md` is the only file kept in Chinese).
- Keep PRs focused; smaller PRs review and revert more easily.
- Update `CLAUDE.md` / `README.md` when behavior or setup changes.

## Scope note

This is a single-maintainer portfolio project, so the pipeline deliberately stops
at "branch protection + required checks + deploy from a green `main`." Staging
environments, manual approval gates, and canary/blue-green releases are
intentionally omitted as overkill for this scale.
