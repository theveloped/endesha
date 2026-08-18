"""The host API (FastAPI): the machine-level control plane next to the bus.

Everything about the *running cell* (devices, programs, commands) stays on
zenoh — providers validate lease/phase/schema there and every client (web,
wfctl, programs) shares that path. This API covers what is about the *host*:

    GET  /health                    process view: supervisor/config alive, active cell
    GET  /cells                     the cell definitions this host can run (+ active)
    GET  /cells/active              the active cell (or null)
    POST /cells/{id}/activate       {runtime?} -> stop the running cell, start this one
    POST /cells/stop                stop the running cell

Later tiers (identity/session, audit, recordings/program files, single-port
serving) live here too; device commands never do.
"""

from __future__ import annotations

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .manager import SupervisorManager


class ActivateRequest(BaseModel):
    runtime: Optional[str] = None


def create_app(manager: SupervisorManager) -> FastAPI:
    app = FastAPI(title="WF host API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.state.manager = manager

    def _cells_payload() -> dict:
        st = manager.status()
        active = st["active"]
        return {
            "cells": [c.to_wire() for c in manager.cells()],
            "active": active,
            "alive": st["alive"],
        }

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, **manager.status()}

    @app.get("/cells")
    def cells() -> dict:
        return _cells_payload()

    @app.get("/cells/active")
    def active() -> dict:
        st = manager.status()
        return {"active": st["active"], "alive": st["alive"]}

    @app.post("/cells/stop")
    def stop() -> dict:
        manager.stop()
        return _cells_payload()

    @app.post("/cells/{cid}/activate")
    def activate(cid: str, req: ActivateRequest | None = None) -> dict:
        runtime = req.runtime if req is not None else None
        try:
            manager.activate(cid, runtime)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _cells_payload()

    return app
