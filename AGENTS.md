# Repository Guidelines

## Project Structure & Module Organization
This repository is a Python web app with an optional CLI and a WeChat mini-program frontend.
- Core backend: `app.py` (Flask API/web routes), `agent.py` (chat/report engine), `config.py`, `file_processor.py`, `code_manager.py`.
- RAG modules: `init_rag.py`, `rag_*.py`.
- Web UI: `templates/` (HTML) and `static/` (JS/CSS/images).
- Mini-program client: `miniprogram/`.
- Runtime/output folders: `uploads/`, `reports/`, `__pycache__/`.
- Historical/backup artifacts (`*.bak`, `server_backup_20251221_190415/`) are reference-only; avoid editing them in normal PRs.

## Build, Test, and Development Commands
Use Python 3.10+ in a virtual environment.
- `python -m venv .venv && .\.venv\Scripts\Activate.ps1` - create and activate venv (PowerShell).
- `pip install -r requirements.txt` - install backend dependencies.
- `python app.py` - run Flask app (default `http://localhost:5000`).
- `python agent.py` - run CLI agent.
- `python test_pdf.py` - run PDF dependency/diagnostic checks.
- `python server_test_rag.py` - run RAG connectivity smoke test.

## Coding Style & Naming Conventions
- Follow PEP 8: 4-space indentation, `snake_case` for functions/variables, `PascalCase` for classes, constants in `UPPER_SNAKE_CASE`.
- Keep Flask route handlers thin; move reusable logic to helper modules.
- Frontend assets: use descriptive lowercase filenames, e.g. `report-display.js`, `style_new.css`.
- Prefer small, focused edits; do not mix feature work with backup cleanup.

## Testing Guidelines
- Current tests are script-style checks (`test_*.py`). Add new tests as `test_<feature>.py` in repo root unless a dedicated test package is introduced.
- For API changes, verify both:
  - Happy path response from `python app.py`.
  - At least one failure/validation scenario.
- For PDF/report changes, always run `python test_pdf.py` before submitting.

## Commit & Pull Request Guidelines
Git history is not available in this workspace snapshot, so use this convention:
- Commit format: `type(scope): short summary` (e.g., `fix(pdf): handle missing font gracefully`).
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`.
- PRs should include: purpose, changed files, test commands run, config/env changes, and screenshots for UI updates (`templates/`/`static/`/`miniprogram/`).

## Security & Configuration Tips
- Keep secrets in `.env`; never hardcode keys or commit credentials.
- Treat `KeyPair-6e51.pem` and production config files as sensitive; do not duplicate or expose them in logs.
- Validate uploaded files and enforce size/type checks when touching upload-related code.
