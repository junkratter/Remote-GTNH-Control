"""Feature modules.

Each subpackage exposes a `router` (FastAPI `APIRouter`) registered from
`app.main.create_app()`. Modules must not import from `app.api.*`
(it is OK the other way around).
"""
