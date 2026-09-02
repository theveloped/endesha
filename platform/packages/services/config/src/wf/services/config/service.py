"""The config store service (design §4.4): realm-less ``config/**`` queryables.

Crash-only: all state lives in the file-backed :class:`ConfigStore`; on
restart everything is re-declared. Keys are realm-less so config traffic is
never captured by the recorder's ``{realm}/**`` subscriber.

Run: ``python -m wf.services.config``.
"""

from __future__ import annotations

import argparse
import threading

import zenoh

from wf.core.audit import QueryAudit
from wf.core.codec import encode
from wf.core.envelope import RecentReplies, Request, fail, ok_value, serve_query
from wf.core.log import get_logger
from wf.core.session import open_session

from . import keys
from .store import ConfigStore

_log = get_logger("wf.services.config.service")


class ConfigService:
    def __init__(self, session: zenoh.Session, store: ConfigStore, *, realm: str | None = None) -> None:
        self.session = session
        self.store = store
        # Config keys are realm-less by design; the audit echo of write
        # commands lives under {realm}/audit/config so the recorder sees who
        # changed what (values themselves stay out of recordings).
        self._audit = QueryAudit(session, realm, "config") if realm else None
        self._recent = RecentReplies()
        self._stop_event = threading.Event()
        self._queryables: list = []
        self._alive_token = None

    def _audited(self, handler):
        return handler if self._audit is None else self._audit.wrap(handler)

    # ── lifecycle ────────────────────────────────────────────────────────

    def start(self) -> None:
        self._queryables = [
            self.session.declare_queryable(keys.frames_glob(), self._on_get),
            self.session.declare_queryable(keys.poses_glob(), self._on_get),
            self.session.declare_queryable(keys.scene_glob(), self._on_get),
            self.session.declare_queryable(keys.intrinsics_glob(), self._on_get),
            self.session.declare_queryable(
                f"{keys.CONFIG_PREFIX}/arm/**", self._on_get
            ),
            self.session.declare_queryable(keys.programs_glob(), self._on_get),
            self.session.declare_queryable(keys.cmd_set(), self._audited(self._on_cmd_set)),
            self.session.declare_queryable(keys.cmd_delete(), self._audited(self._on_cmd_delete)),
        ]
        self._alive_token = self.session.liveliness().declare_token(keys.alive())
        _log.info("config service up: dir=%s", self.store.root_dir)

    def run_forever(self) -> None:
        try:
            self._stop_event.wait()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        self._stop_event.set()
        _log.info("config service stopped")

    # ── queryables ───────────────────────────────────────────────────────

    def _on_get(self, query: zenoh.Query) -> None:
        try:
            for key, val in self.store.get_matching(str(query.key_expr)).items():
                query.reply(key, encode(val))
        except Exception:
            _log.exception("config GET failed: %s", query.key_expr)

    @staticmethod
    def _store_error(exc: ValueError) -> dict:
        """The store's machine-readable "reason:detail" strings map straight
        onto the envelope (``invalid_key:``, ``bad_frame:``, ``cycle:``, …)."""
        head, _, detail = str(exc).partition(":")
        return fail("invalid", head or "bad_request", detail or None)

    def _on_cmd_set(self, query: zenoh.Query) -> None:
        serve_query(query, self._do_set, recent=self._recent)

    def _do_set(self, req: Request) -> dict:
        try:
            key, value = req.args["key"], req.args["value"]
        except Exception as exc:  # noqa: BLE001
            return fail("invalid", "bad_request", repr(exc))
        try:
            revision = self.store.set(key, value)
        except ValueError as exc:
            return self._store_error(exc)
        except Exception as exc:  # noqa: BLE001
            return fail("internal", "set_failed", repr(exc))
        # Publish the STORED (normalized, revision-stamped) value on its own
        # key so live subscribers (e.g. the sim camera page) see the edit
        # without re-GETting. config/** stays queryable too; this only adds
        # a latest-wins sample on change.
        stored = self.store.get_matching(key).get(key, value)
        self.session.put(key, encode(stored))
        return ok_value({"revision": revision})

    def _on_cmd_delete(self, query: zenoh.Query) -> None:
        serve_query(query, self._do_delete, recent=self._recent)

    def _do_delete(self, req: Request) -> dict:
        try:
            key = req.args["key"]
        except Exception as exc:  # noqa: BLE001
            return fail("invalid", "bad_request", repr(exc))
        try:
            self.store.delete(key)
        except ValueError as exc:
            return self._store_error(exc)
        except Exception as exc:  # noqa: BLE001
            return fail("internal", "delete_failed", repr(exc))
        # Empty-payload tombstone so live subscribers drop the entry (mirrors
        # the runtime scene layer's delete convention in scene_live.py).
        self.session.put(key, encode({}))
        return ok_value()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="config", description=__doc__)
    parser.add_argument(
        "--dir",
        default="deploy/config",
        help="store directory holding store.yaml + history.jsonl (default deploy/config)",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    parser.add_argument(
        "--realm",
        default=None,
        help="realm for the {realm}/audit/config echo of write commands (no echo when omitted)",
    )
    args = parser.parse_args(argv)

    session = open_session(args.zenoh_config)
    service = ConfigService(session, ConfigStore(args.dir), realm=args.realm)
    try:
        service.start()
        service.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
