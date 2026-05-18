from app.api.automate import router as automate_router
from app.api.info import router as info_router
from app.api.task import router as task_router

__all__ = ["task_router", "automate_router", "info_router"]
