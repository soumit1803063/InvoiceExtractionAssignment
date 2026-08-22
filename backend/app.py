from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import Response
from starlette.types import Scope

from .container import ApplicationContainer
from .controllers.controller import build_router
from .settings import Settings


class SinglePageApplicationFiles(StaticFiles):

    async def get_response(self, path: str, scope: Scope) -> Response:
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as error:
            if error.status_code != 404:
                raise
            return await super().get_response("index.html", scope)


def create_app(settings: Settings) -> FastAPI:
    container = ApplicationContainer(settings)
    container.intake_service.restart_stranded()
    app = FastAPI(title="Invoice Intake", version="1.0.0")
    app.include_router(build_router(container))
    if settings.frontend_directory.is_dir():
        app.mount(
            "/",
            SinglePageApplicationFiles(directory=settings.frontend_directory, html=True),
            name="frontend",
        )
    return app
