# Cleanup Policy

This repository keeps runtime and source artifacts separated.

## Do not commit

- Backup folders and snapshots (for example `_cleanup_archive/`, `*.bak`, `*.backup*`)
- Runtime logs (`*.log`, `logs/*.jsonl`)
- Generated report files in `reports/`
- Local cache or tooling temp folders (for example `.vite/`)
- Local SQLite runtime metadata (`db/*.db`)

## Allowed runtime folders

- `uploads/` and `reports/` are runtime folders and may exist locally.
- Keep a `.gitkeep` marker if an empty runtime folder must be preserved.

## API version rule

- Web clients must use `/api/v1/*`.
- Legacy `/api/*` routes are deprecated and return migration errors.

