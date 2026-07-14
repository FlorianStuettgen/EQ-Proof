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
except ImportError:  # pragma: no cover - optional web extra
    FastAPI = None  # type: ignore[assignment]
    HTTPException = RuntimeError  # type: ignore[assignment]
    Request = Any  # type: ignore[assignment]
    JSONResponse = None  # type: ignore[assignment]
    StaticFiles = None  # type: ignore[assignment]

from .control_room import build_control_room
from .controls import CATALOGUE, ControlsError, analyze, load_csv, load_equations, parse_xer

MAX_UPLOAD_BYTES = 50 * 1024 * 1024
WEB_ROOT = Path(__file__).with_name("web")


async def _save_upload(upload: Any, directory: Path, fallback_name: str) -> Path:
    name = Path(upload.filename or fallback_name).name
    target = directory / name
    total = 0
    with target.open("wb") as handle:
        while chunk := await upload.read(1024 * 1024):
            total += len(chunk)
            if total > MAX_UPLOAD_BYTES:
                raise ControlsError(f"{name} exceeds the 50 MiB upload limit")
            handle.write(chunk)
    return target


def create_app() -> Any:
    if FastAPI is None or JSONResponse is None or StaticFiles is None:
        raise RuntimeError(
            "Web dependencies are not installed. Run: python -m pip install 'eq-proof[web]'"
        )
    app = FastAPI(
        title="EQ-Proof Control Room",
        version="1.3.0",
        docs_url=None,
        redoc_url=None,
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
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ok", "mode": "local-first"}

    @app.get("/api/catalogue")
    async def catalogue() -> list[dict[str, Any]]:
        return [equation.__dict__ for equation in CATALOGUE]

    @app.get("/api/demo")
    async def demo() -> Any:
        path = WEB_ROOT / "demo-data.json"
        if not path.exists():
            raise HTTPException(status_code=503, detail="Demo data has not been generated")
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))

    @app.post("/api/analyze")
    async def analyze_uploads(request: Request) -> Any:
        try:
            form = await request.form()
            p6_xer = form.getlist("p6_xer")
            cost_csv = form.getlist("cost_csv")
            equation_pack = form.getlist("equation_pack")
            custom_equations = str(form.get("custom_equations", "[]"))
            catalogue_ids = str(form.get("catalogue_ids", ""))
            with tempfile.TemporaryDirectory(prefix="eq-proof-") as temporary:
                directory = Path(temporary)
                records: list[dict[str, Any]] = []
                sources: list[str] = []
                for index, upload in enumerate(p6_xer):
                    if not hasattr(upload, "read"):
                        continue
                    path = await _save_upload(upload, directory, f"schedule-{index}.xer")
                    records.extend(parse_xer(path))
                    sources.append(upload.filename or path.name)
                for index, upload in enumerate(cost_csv):
                    if not hasattr(upload, "read"):
                        continue
                    path = await _save_upload(upload, directory, f"cost-{index}.csv")
                    records.extend(load_csv(path))
                    sources.append(upload.filename or path.name)
                if not records:
                    raise ControlsError("Upload at least one P6 XER or cost CSV file")

                enabled = {value for value in catalogue_ids.split(",") if value}
                equations = [item for item in CATALOGUE if not enabled or item.id in enabled]
                for index, upload in enumerate(equation_pack):
                    if not hasattr(upload, "read"):
                        continue
                    path = await _save_upload(upload, directory, f"equations-{index}.json")
                    equations.extend(load_equations(path))
                    sources.append(upload.filename or path.name)
                custom_document = json.loads(custom_equations)
                if custom_document:
                    path = directory / "inline-equations.json"
                    path.write_text(json.dumps(custom_document), encoding="utf-8")
                    equations.extend(load_equations(path))
                    sources.append("inline-equations")

                result = analyze(records, equations=equations, sources=sources)
                return JSONResponse(build_control_room(records, result))
        except (ControlsError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    app.mount("/", StaticFiles(directory=WEB_ROOT, html=True), name="web")
    return app
