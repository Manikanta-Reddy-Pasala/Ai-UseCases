"""API calling tool - make HTTP requests to external APIs."""

import aiohttp
import json


BLOCKED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "metadata.google"}


async def _api_call(url: str, method: str = "GET", headers: dict = None,
                    body: str = None, timeout: int = 15) -> str:
    """Make an HTTP request to an external API."""
    # Safety: block internal/metadata endpoints
    from urllib.parse import urlparse
    parsed = urlparse(url)
    if parsed.hostname in BLOCKED_HOSTS or (parsed.hostname and parsed.hostname.startswith("10.")):
        return "Blocked: internal/metadata endpoints not allowed"

    if method.upper() not in {"GET", "POST", "PUT", "PATCH"}:
        return f"Blocked: method {method} not allowed (use GET, POST, PUT, PATCH)"

    try:
        async with aiohttp.ClientSession() as session:
            kwargs = {
                "url": url,
                "headers": headers or {},
                "timeout": aiohttp.ClientTimeout(total=timeout)
            }
            if body and method.upper() in {"POST", "PUT", "PATCH"}:
                kwargs["data"] = body
                if "Content-Type" not in (headers or {}):
                    kwargs["headers"]["Content-Type"] = "application/json"

            async with session.request(method.upper(), **kwargs) as resp:
                status = resp.status
                resp_headers = dict(resp.headers)
                try:
                    resp_body = await resp.text()
                    # Try to pretty-print JSON
                    try:
                        resp_body = json.dumps(json.loads(resp_body), indent=2)
                    except (json.JSONDecodeError, ValueError):
                        pass
                except Exception:
                    resp_body = "<binary response>"

                return f"Status: {status}\nHeaders: {json.dumps({k: v for k, v in list(resp_headers.items())[:10]})}\nBody:\n{resp_body[:5000]}"

    except Exception as e:
        return f"API call error: {e}"


api_call_tool = {
    "definition": {
        "name": "api_call",
        "description": "Make an HTTP request to an external API. Supports GET, POST, PUT, PATCH.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "Full URL to call"},
                "method": {"type": "string", "description": "HTTP method (GET, POST, PUT, PATCH)", "default": "GET"},
                "headers": {"type": "object", "description": "Request headers", "default": {}},
                "body": {"type": "string", "description": "Request body (for POST/PUT/PATCH)"},
                "timeout": {"type": "integer", "description": "Timeout in seconds", "default": 15}
            },
            "required": ["url"]
        }
    },
    "handler": _api_call
}
