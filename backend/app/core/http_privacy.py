"""Response privacy without buffering streams or changing authentication behavior."""
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.datastructures import MutableHeaders

PRIVATE_HEADERS = {"Cache-Control": "no-store", "Pragma": "no-cache",
                   "X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}


class APIPrivacyMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        path = scope.get("path", "")
        protected = scope["type"] == "http" and any(
            path == prefix or path.startswith(prefix + "/") for prefix in ("/api", "/openapi"))

        async def private_send(message):
            if protected and message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers.update(PRIVATE_HEADERS)
            await send(message)

        await self.app(scope, receive, private_send)


async def private_validation_error(request, exc: RequestValidationError):
    # Pydantic's input/ctx (and sometimes messages) contain submitted passwords,
    # OTPs, private prompts or keys. Preserve field locations, never their values.
    detail = [{"loc": list(error["loc"]), "type": error["type"],
               "msg": "Missing required field" if error["type"] == "missing" else "Invalid value"}
              for error in exc.errors()[:32]]
    return JSONResponse(status_code=422, content={"detail": detail},
                        headers=PRIVATE_HEADERS)


async def private_server_error(request, exc):
    # Starlette's outer ServerErrorMiddleware otherwise bypasses user middleware.
    return JSONResponse(status_code=500, content={"detail": "Internal server error"},
                        headers=PRIVATE_HEADERS)


def install_http_privacy(app):
    app.add_middleware(APIPrivacyMiddleware)
    app.add_exception_handler(RequestValidationError, private_validation_error)
    app.add_exception_handler(Exception, private_server_error)
