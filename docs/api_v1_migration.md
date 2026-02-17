# API v1 Migration Notes

## Base rule

- New endpoints: `/api/v1/*`
- Legacy `/api/*`: returns HTTP `410` with:
  - `error.code = API_VERSION_MIGRATED`
  - `error.message = Use /api/v1/* endpoints`

## Key endpoint mapping (Web)

- `POST /api/chat` -> `POST /api/v1/chat`
- `POST /api/chat/stream` -> `POST /api/v1/chat/stream`
- `POST /api/upload` -> `POST /api/v1/files/upload`
- `GET /api/history` -> `GET /api/v1/sessions/history`
- `POST /api/history/clear` -> `POST /api/v1/sessions/clear`
- `GET /api/sessions` -> `GET /api/v1/sessions`
- `GET /api/user/usage` -> `GET /api/v1/user/usage`
- `POST /api/verify-code` -> `POST /api/v1/verify-code`
- `GET /api/config` -> `GET /api/v1/config`

## New file-id based download

- `GET /api/v1/files/{file_id}` for metadata
- `GET /api/v1/files/{file_id}/download` for download
- Report status:
  - `GET /api/v1/reports/{file_id}/pdf-status`
  - `POST /api/v1/reports/{file_id}/convert-pdf`

## Backfill

Run:

```bash
python scripts/backfill_file_registry.py
```

This scans `uploads/` and `reports/` and registers files into `db/app_meta.db`.
