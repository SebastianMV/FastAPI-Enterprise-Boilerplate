# Copyright (c) 2025-2026 Sebastián Muñoz
# Licensed under the MIT License

"""
Request-ID Middleware (Pure ASGI).

Assigns a unique UUID to every incoming request and includes it
in the response as the `X-Request-ID` header.  If the client
already sends the header, its value is preserved.
"""

import re
import uuid

from starlette.types import ASGIApp, Message, Receive, Scope, Send

# Valid request ID: 1-128 printable ASCII characters (letters, digits, hyphens, underscores)
_REQUEST_ID_PATTERN = re.compile(r"^[a-zA-Z0-9\-_]{1,128}$")


class RequestIDMiddleware:
    """
    Pure ASGI middleware that injects a unique request ID.

    - Reads an existing ``X-Request-ID`` from the request headers.
    - If absent, generates a new UUID-4.
    - Stores the ID in ``scope["state"]["request_id"]`` so that
      downstream middleware / endpoints can access it.
    - Adds ``X-Request-ID`` to every HTTP response.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] not in ("http", "websocket"):
            await self.app(scope, receive, send)
            return

        # --- Extract or generate request ID ---
        request_id: str | None = None
        for header_name, header_value in scope.get("headers", []):
            if header_name == b"x-request-id":
                raw = header_value.decode("latin-1")
                # Validate format: reject overlong or malformed IDs
                if _REQUEST_ID_PATTERN.match(raw):
                    request_id = raw
                break

        if not request_id:
            request_id = str(uuid.uuid4())

        # Store in scope for access by endpoints / logging
        scope.setdefault("state", {})
        scope["state"]["request_id"] = request_id

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-request-id", request_id.encode("latin-1")))  # type: ignore[union-attr]
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_request_id)
