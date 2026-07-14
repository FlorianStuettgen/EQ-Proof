"""Local-first FastAPI application for the EQ-Proof Control Room."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from fastapi.staticfiles import StaticFiles
    from starlette.middleware.trustedhost import TrustedHostMiddleware
except ImportError:  # pragma: no cover - optional web extra
    FastAPI = None  # type: ignore[assignment]
    HTTPException = RuntimeError  # type: ignore[assignment]
    Request = Any  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]
    StaticFiles = None  # type: ignore[assignment]
    TrustedHostMiddleware = None  # type: ignore[assignment]

from .control_room import build_control_room
from .controls import (
    CATALOGUE,
    ControlsError,
    analyze,
    load_csv,
    load_equations,
    parse_equations,
    parse_xer,
)

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
MAX_TOTAL_UPLOAD_BYTES = 200 * 1024 * 1024
MAX_UPLOAD_FILES = 20
MAX_INLINE_EQUATION_BYTES = 256 * 1024
WEB_ROOT = Path(__file__).with_name("web")


async def _save_upload(
    upload: Any,
    directory: Path,
    slot: str,
    remaining_bytes: int,
) -> tuple[Path, int]:
    original_name = Path(upload.filename or "upload").name
    target = directory / f"{slot}-{original_name}"
    total = 0
    with target.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise ControlsError(
                    f"{original_name} exceeds the 50 MiB per-file limit"
                )
            if total > remaining_bytes:
                raise ControlsError("Uploads exceed the 200 MiB request limit")
            handle.write(chunk)
    return target, total


def create_app() -> Any:
    if (
        FastAPI is None
        or JSONResponse is None
        or StaticFiles is None
        or TrustedHostMiddleware is None
    ):
        raise RuntimeError(
            "Web dependencies are not installed. Run: python -m pip install 'eq-proof[web]'"
        )
    app = FastAPI(
        title="EQ-Proof Control Room",
        version="1.4.0",
        docs_url=None,
        redoc_url=None,
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["127.0.0.1", "localhost", "[::1]", "testserver"],
    )

    @app.middleware("http")
    async def security_headers(request: Any, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; style-src 'self'; "
            "img-src 'self' data:; connect-src 'self'; object-src 'none'; "
            "base-uri 'none'; frame-ancestors 'none'; form-action 'self'"
        )
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "mode": "local-first"}

    @app.get("/api/catalogue")
    async def catalogue() -> list[dict[str, Any]]:
        return [equation.__dict__ for equation in CATALOGUE]

    @app.post("/api/equations/validate")
    async def validate_equations(request: Request) -> Any:
        try:
            raw = await request.body()
            if len(raw) > MAX_INLINE_EQUATION_BYTES:
                raise ControlsError(
                    "Equation request exceeds the 256 KiB limit"
                )
            document = json.loads(raw or b"[]")
            if isinstance(document, dict):
                document = [document]
            equations = parse_equations(document)
            return JSONResponse(
                [equation.__dict__ for equation in equations]
            )
        except (
            ControlsError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/demo")
    async def demo() -> Any:
        path = WEB_ROOT / "demo-data.json"
        if not path.exists():
            raise HTTPException(
                status_code=503,
                detail="Demo data has not been generated",
            )
        return JSONResponse(
            json.loads(path.read_text(encoding="utf-8"))
        )

    @app.post("/api/analyze")
    async def analyze_uploads(request: Request) -> Any:
        try:
            form = await request.form()
            p6_xer = [
                item
                for item in form.getlist("p6_xer")
                if hasattr(item, "read")
            ]
            cost_csv = [
                item
                for item in form.getlist("cost_csv")
                if hasattr(item, "read")
            ]
            equation_pack = [
                item
                for item in form.getlist("equation_pack")
                if hasattr(item, "read")
            ]
            uploads = [*p6_xer, *cost_csv, *equation_pack]
            if len(uploads) > MAX_UPLOAD_FILES:
                raise ControlsError(
                    f"A request may contain at most {MAX_UPLOAD_FILES} files"
                )
            custom_equations = str(
                form.get("custom_equations", "[]")
            )
            if (
                len(custom_equations.encode("utf-8"))
                > MAX_INLINE_EQUATION_BYTES
            ):
                raise ControlsError(
                    "Inline equations exceed the 256 KiB limit"
                )
            catalogue_value = form.get("catalogue_ids")
            currency = str(form.get("currency", "USD")).upper()
            if len(currency) != 3 or not currency.isalpha():
                raise ControlsError(
                    "currency must be a three-letter code"
                )

            with tempfile.TemporaryDirectory(
                prefix="eq-proof-"
            ) as temporary:
                directory = Path(temporary)
                records: list[dict[str, Any]] = []
                sources: list[str] = []
                consumed = 0
                for index, upload in enumerate(p6_xer):
                    path, size = await _save_upload(
                        upload,
                        directory,
                        f"p6-{index}",
                        MAX_TOTAL_UPLOAD_BYTES - consumed,
                    )
                    consumed += size
                    records.extend(parse_xer(path))
                    sources.append(
                        Path(upload.filename or path.name).name
                    )
                for index, upload in enumerate(cost_csv):
                    path, size = await _save_upload(
                        upload,
                        directory,
                        f"cost-{index}",
                        MAX_TOTAL_UPLOAD_BYTES - consumed,
                    )
                    consumed += size
                    records.extend(load_csv(path))
                    sources.append(
                        Path(upload.filename or path.name).name
                    )
                if not records:
                    raise ControlsError(
                        "Upload at least one P6 XER or cost CSV file"
                    )

                if catalogue_value is None:
                    equations = list(CATALOGUE)
                else:
                    requested = {
                        value
                        for value in str(catalogue_value).split(",")
                        if value
                    }
                    known = {item.id for item in CATALOGUE}
                    unknown = requested - known
                    if unknown:
                        raise ControlsError(
                            "Unknown catalogue equations: "
                            + ", ".join(sorted(unknown))
                        )
                    equations = [
                        item for item in CATALOGUE if item.id in requested
                    ]

                for index, upload in enumerate(equation_pack):
                    path, size = await _save_upload(
                        upload,
                        directory,
                        f"equations-{index}",
                        MAX_TOTAL_UPLOAD_BYTES - consumed,
                    )
                    consumed += size
                    equations.extend(load_equations(path))
                    sources.append(
                        Path(upload.filename or path.name).name
                    )
                custom_document = json.loads(custom_equations)
                if custom_document:
                    equations.extend(
                        parse_equations(custom_document)
                    )
                    sources.append("inline-equations")

                result = analyze(
                    records,
                    equations=equations,
                    sources=sources,
                )
                return JSONResponse(
                    build_control_room(
                        records,
                        result,
                        currency=currency,
                    )
                )
        except (
            ControlsError,
            OSError,
            json.JSONDecodeError,
            KeyError,
            TypeError,
            ValueError,
        ) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    app.mount(
        "/",
        StaticFiles(directory=WEB_ROOT, html=True),
        name="web",
    )
    return app
