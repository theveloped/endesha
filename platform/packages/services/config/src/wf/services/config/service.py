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

from wf.core.codec import decode, encode
from wf.core.log import get_logger
from wf.core.session import open_session

from . import keys
from .store import ConfigStore

_log = get_logger("wf.services.config.service")


class ConfigService:
    def __init__(self, session: zenoh.Session, store: ConfigStore) -> None:
        self.session = session
        self.store = store
        self._stop_event = threading.Event()
        self._queryables: list = []
        self._alive_token = None

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
            self.session.declare_queryable(keys.cmd_set(), self._on_cmd_set),
            self.session.declare_queryable(keys.cmd_delete(), self._on_cmd_delete),
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

    def _on_cmd_set(self, query: zenoh.Query) -> None:
        key = str(query.key_expr)
        try:
            req = decode(query.payload) if query.payload is not None else {}
            revision = self.store.set(req["key"], req["value"])
            query.reply(
                key, encode({"ok": True, "revision": revision, "error": None})
            )
        except ValueError as exc:
            query.reply(
                key, encode({"ok": False, "revision": None, "error": str(exc)})
            )
        except Exception as exc:
            query.reply(
                key, encode({"ok": False, "revision": None, "error": repr(exc)})
            )

    def _on_cmd_delete(self, query: zenoh.Query) -> None:
        key = str(query.key_expr)
        try:
            req = decode(query.payload) if query.payload is not None else {}
            self.store.delete(req["key"])
            query.reply(key, encode({"ok": True, "error": None}))
        except ValueError as exc:
            query.reply(key, encode({"ok": False, "error": str(exc)}))
        except Exception as exc:
            query.reply(key, encode({"ok": False, "error": repr(exc)}))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="config", description=__doc__)
    parser.add_argument(
        "--dir",
        default="deploy/config",
        help="store directory holding store.yaml + history.jsonl (default deploy/config)",
    )
    parser.add_argument("--zenoh-config", default=None, help="zenoh config path")
    args = parser.parse_args(argv)

    session = open_session(args.zenoh_config)
    service = ConfigService(session, ConfigStore(args.dir))
    try:
        service.start()
        service.run_forever()
    finally:
        session.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
