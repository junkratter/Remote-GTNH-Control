"""`app.core` package.

Submodules import each other freely; we keep this ``__init__`` empty to
avoid eager re-export cycles (e.g. ``tasks`` ↔ ``db.session``).
Import names directly from submodules in application code.
"""
