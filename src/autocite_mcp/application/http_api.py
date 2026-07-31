from __future__ import annotations

import argparse
import base64
import hmac
import json
import os
import secrets
import sys
import traceback
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from ipaddress import ip_address
from typing import Any
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

from .models import DecisionState
from .service import (
    ApplicationService,
    ApplicationServiceError,
    InvalidReviewDecision,
    UnsupportedDocumentFormat,
)
from .store import (
    RevisionConflict,
    ReviewJobNotFound,
    SessionNotFound,
    SessionStoreError,
)

_MAX_REQUEST_BYTES = 25 * 1024 * 1024
_ALLOWED_ORIGINS = {
    "tauri://localhost",
    "https://tauri.localhost",
    "http://tauri.localhost",
}


class AutoCiteApplicationServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self,
        address: tuple[str, int],
        *,
        service: ApplicationService,
        token: str,
    ) -> None:
        super().__init__(address, AutoCiteApplicationHandler)
        self.service = service
        self.token = token


class AutoCiteApplicationHandler(BaseHTTPRequestHandler):
    server: AutoCiteApplicationServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        if os.environ.get("AUTOCITE_APP_QUIET") != "1":
            super().log_message(format, *args)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.send_header("Access-Control-Allow-Headers", "Authorization, Content-Type, X-AutoCite-Token")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        self._dispatch("GET")

    def do_POST(self) -> None:  # noqa: N802
        self._dispatch("POST")

    def do_PATCH(self) -> None:  # noqa: N802
        self._dispatch("PATCH")

    def do_DELETE(self) -> None:  # noqa: N802
        self._dispatch("DELETE")

    def _dispatch(self, method: str) -> None:
        request_id = uuid4().hex
        try:
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            if path != "/health" and not self._authorized():
                self._send_json(
                    HTTPStatus.UNAUTHORIZED,
                    {"error": "unauthorized", "request_id": request_id},
                )
                return
            body = self._read_json() if method in {"POST", "PATCH"} else {}
            result, status = self._route(method, path, parse_qs(parsed.query), body)
            self._send_json(status, {"request_id": request_id, **result})
        except SessionNotFound as exc:
            self._send_error_json(HTTPStatus.NOT_FOUND, "session_not_found", str(exc), request_id)
        except ReviewJobNotFound as exc:
            self._send_error_json(HTTPStatus.NOT_FOUND, "review_job_not_found", str(exc), request_id)
        except RevisionConflict as exc:
            self._send_json(
                HTTPStatus.CONFLICT,
                {
                    "error": "revision_conflict",
                    "message": str(exc),
                    "session_id": exc.session_id,
                    "expected_revision": exc.expected,
                    "current_revision": exc.actual,
                    "request_id": request_id,
                },
            )
        except (InvalidReviewDecision, UnsupportedDocumentFormat, ValueError) as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "invalid_request", str(exc), request_id)
        except FileNotFoundError as exc:
            self._send_error_json(HTTPStatus.NOT_FOUND, "file_not_found", str(exc), request_id)
        except json.JSONDecodeError as exc:
            self._send_error_json(HTTPStatus.BAD_REQUEST, "invalid_json", str(exc), request_id)
        except (ApplicationServiceError, SessionStoreError) as exc:
            self._send_error_json(HTTPStatus.UNPROCESSABLE_ENTITY, "application_error", str(exc), request_id)
        except Exception as exc:  # pragma: no cover - final process boundary
            if os.environ.get("AUTOCITE_APP_DEBUG") == "1":
                traceback.print_exc()
            self._send_error_json(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_error",
                f"{type(exc).__name__}: {exc}",
                request_id,
            )

    def _route(
        self,
        method: str,
        path: str,
        query: dict[str, list[str]],
        body: dict[str, Any],
    ) -> tuple[dict[str, Any], HTTPStatus]:
        service = self.server.service
        if method == "GET" and path == "/health":
            return (
                {
                    "status": "ok",
                    "service": "autocite-application",
                    "api_version": 1,
                    "authenticated": self._authorized(),
                    "persistence": "sqlite",
                    "network_scope": "loopback",
                },
                HTTPStatus.OK,
            )
        if method == "GET" and path == "/sessions":
            limit = int(query.get("limit", ["50"])[0])
            offset = int(query.get("offset", ["0"])[0])
            return service.list_sessions(limit=limit, offset=offset), HTTPStatus.OK
        if method == "POST" and path == "/sessions":
            session = service.create_session(
                title=str(body.get("title") or "Untitled document"),
                text=str(body.get("text") or ""),
                source_format=str(body.get("source_format") or "md"),
                metadata=body.get("metadata") if isinstance(body.get("metadata"), dict) else None,
            )
            return {"session": session.to_dict()}, HTTPStatus.CREATED
        if method == "POST" and path == "/sessions/import":
            session = service.import_path(str(body["path"]))
            return {"session": session.to_dict()}, HTTPStatus.CREATED
        if method == "GET" and path.startswith("/jobs/"):
            job_id = path.split("/", 2)[2]
            return {"job": service.get_review_job(job_id)}, HTTPStatus.OK

        parts = [part for part in path.split("/") if part]
        if len(parts) >= 2 and parts[0] == "sessions":
            session_id = parts[1]
            if len(parts) == 2:
                if method == "GET":
                    return {"session": service.get_session(session_id)}, HTTPStatus.OK
                if method == "PATCH":
                    session = service.update_session(
                        session_id,
                        expected_revision=int(body["expected_revision"]),
                        text=body.get("text") if isinstance(body.get("text"), str) else None,
                        title=body.get("title") if isinstance(body.get("title"), str) else None,
                        editor_state=body.get("editor_state")
                        if isinstance(body.get("editor_state"), dict)
                        else None,
                    )
                    return {"session": session.to_dict()}, HTTPStatus.OK
                if method == "DELETE":
                    service.store.delete_session(session_id)
                    return {"deleted": True, "session_id": session_id}, HTTPStatus.OK
            if len(parts) == 3 and method == "POST":
                action = parts[2]
                if action == "review":
                    job = service.review_session_sync(
                        session_id,
                        expected_revision=int(body["expected_revision"]),
                        mode=body.get("mode"),
                        jurisdiction=body.get("jurisdiction"),
                        deep_review=bool(body.get("deep_review", False)),
                        use_local_model=bool(body.get("use_local_model", False)),
                    )
                    return {"job": job.to_dict()}, HTTPStatus.OK
                if action == "decision":
                    result = service.decide_issue(
                        session_id,
                        issue_id=str(body["issue_id"]),
                        decision=DecisionState(str(body["decision"])),
                        expected_revision=int(body["expected_revision"]),
                        rationale=body.get("rationale"),
                    )
                    return result, HTTPStatus.OK
                if action == "apply-safe":
                    identifiers = body.get("issue_ids")
                    if not isinstance(identifiers, list) or not all(
                        isinstance(item, str) for item in identifiers
                    ):
                        raise ValueError("issue_ids must be a list of strings")
                    result = service.apply_safe_issues(
                        session_id,
                        issue_ids=identifiers,
                        expected_revision=int(body["expected_revision"]),
                        rationale=body.get("rationale"),
                    )
                    return result, HTTPStatus.OK
                if action == "context-preview":
                    spans = body.get("focus_spans")
                    focus_spans = None
                    if isinstance(spans, list):
                        focus_spans = [
                            (int(item[0]), int(item[1]))
                            for item in spans
                            if isinstance(item, (list, tuple)) and len(item) >= 2
                        ]
                    result = service.context_preview(
                        session_id,
                        focus_spans=focus_spans,
                        max_characters=int(body["max_characters"])
                        if body.get("max_characters") is not None
                        else None,
                        include_text=bool(body.get("include_text", False)),
                    )
                    return {"reduction": result}, HTTPStatus.OK
                if action == "export":
                    artifact = service.export_session(
                        session_id,
                        output_format=str(body.get("format") or "docx"),
                        destination=body.get("destination"),
                    )
                    result = {"artifact": artifact.summary()}
                    if artifact.path is None:
                        result["artifact"]["content_base64"] = base64.b64encode(
                            artifact.content
                        ).decode("ascii")
                    return result, HTTPStatus.OK
        return {"error": "not_found", "message": f"No route for {method} {path}"}, HTTPStatus.NOT_FOUND

    def _authorized(self) -> bool:
        supplied = self.headers.get("X-AutoCite-Token")
        authorization = self.headers.get("Authorization", "")
        if authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
        return bool(supplied) and hmac.compare_digest(supplied, self.server.token)

    def _read_json(self) -> dict[str, Any]:
        length_header = self.headers.get("Content-Length", "0")
        length = int(length_header)
        if length < 0 or length > _MAX_REQUEST_BYTES:
            raise ValueError(f"Request body exceeds {_MAX_REQUEST_BYTES} bytes")
        if length == 0:
            return {}
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("JSON request body must be an object")
        return payload

    def _send_error_json(
        self,
        status: HTTPStatus,
        code: str,
        message: str,
        request_id: str,
    ) -> None:
        self._send_json(
            status,
            {"error": code, "message": message, "request_id": request_id},
        )

    def _send_json(self, status: HTTPStatus, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode(
            "utf-8"
        )
        self.send_response(status)
        self._send_cors_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)

    def _send_cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin and _origin_allowed(origin):
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")


def _origin_allowed(origin: str) -> bool:
    if origin in _ALLOWED_ORIGINS:
        return True
    parsed = urlparse(origin)
    return parsed.scheme in {"http", "https"} and parsed.hostname in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _is_loopback(host: str) -> bool:
    if host.lower() == "localhost":
        return True
    try:
        return ip_address(host).is_loopback
    except ValueError:
        return False


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="AutoCite local application API")
    parser.add_argument("--host", default=os.environ.get("AUTOCITE_APP_HOST", "127.0.0.1"))
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("AUTOCITE_APP_PORT", "8765"))
    )
    parser.add_argument("--token", default=os.environ.get("AUTOCITE_API_TOKEN"))
    parser.add_argument("--database", default=os.environ.get("AUTOCITE_SESSION_DB"))
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)
    if not _is_loopback(args.host) and os.environ.get("AUTOCITE_ALLOW_REMOTE") != "1":
        raise SystemExit(
            "AutoCite's application API is loopback-only. Set AUTOCITE_ALLOW_REMOTE=1 "
            "only for an authenticated, intentionally remote deployment."
        )
    token = args.token or secrets.token_urlsafe(32)
    if not _is_loopback(args.host) and not args.token:
        raise SystemExit("A configured API token is required for non-loopback binding")
    service = ApplicationService()
    if args.database:
        from .store import SessionStore

        service = ApplicationService(store=SessionStore(args.database))
    server = AutoCiteApplicationServer(
        (args.host, args.port), service=service, token=token
    )
    host, port = server.server_address[:2]
    ready = {
        "event": "ready",
        "service": "autocite-application",
        "host": host,
        "port": port,
        "token": token if os.environ.get("AUTOCITE_PRINT_TOKEN") == "1" else None,
        "pid": os.getpid(),
    }
    print(json.dumps(ready, separators=(",", ":")), flush=True)
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main(sys.argv[1:])
