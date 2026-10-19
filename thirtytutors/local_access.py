"""Per-process launcher capability + same-origin checks for local HTTP/WS."""

import secrets
from http.cookies import SimpleCookie
from urllib.parse import parse_qs, urlsplit

LAUNCH_TOKEN = secrets.token_urlsafe(32)
COOKIE = "companion_session"


class LocalAccessMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in ("http", "websocket"):
            return await self.app(scope, receive, send)
        headers = {k.decode().lower(): v.decode() for k, v in scope.get("headers", [])}
        host = headers.get("host", "")
        hostname = urlsplit("http://" + host).hostname
        origin = headers.get("origin")
        origin_ok = origin is None or origin in ("http://" + host, "https://" + host)
        cookies = SimpleCookie()
        try:
            cookies.load(headers.get("cookie", ""))
            credential = cookies[COOKIE].value if COOKIE in cookies else ""
        except Exception:
            credential = ""
        credential = headers.get("x-companion-token", credential)
        query = parse_qs(scope.get("query_string", b"").decode())
        bootstrap = scope["type"] == "http" and scope["path"] in ("/", "/landing")
        launch = query.get("launch", [""])[0] if bootstrap else ""
        authenticated = secrets.compare_digest(credential, LAUNCH_TOKEN) or (
            bootstrap and secrets.compare_digest(launch, LAUNCH_TOKEN)
        )
        if hostname not in ("127.0.0.1", "localhost") or not origin_ok or not authenticated:
            if scope["type"] == "websocket":
                await send({"type": "websocket.close", "code": 1008})
            else:
                body = b"Open Companion Lite from its Windows launcher."
                await send({"type": "http.response.start", "status": 403, "headers": [(b"content-type", b"text/plain")]})
                await send({"type": "http.response.body", "body": body})
            return

        async def send_response(message):
            if message["type"] == "http.response.start":
                extra = [
                    (b"referrer-policy", b"no-referrer"),
                    (b"x-content-type-options", b"nosniff"),
                    (
                        b"content-security-policy",
                        b"default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'",
                    ),
                ]
                if bootstrap:
                    extra.append((b"set-cookie", f"{COOKIE}={LAUNCH_TOKEN}; HttpOnly; SameSite=Strict; Path=/".encode()))
                message.setdefault("headers", []).extend(extra)
            await send(message)

        await self.app(scope, receive, send_response)
