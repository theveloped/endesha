"""The `task` contract key space — statechart task layer (design: task_runner).

``{flow}`` is the YAML statechart ``name``. ``state`` is latest-wins (DROP);
``result`` is the terminal aggregate (DROP). ``cmd/start`` and ``cmd/abort`` are
queryables. All keys carry the realm prefix.
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str, flow: str) -> str:
    return key(realm_prefix(realm), "task", flow)


def state(realm: str, flow: str) -> str:
    """``{realm}/task/{flow}/state`` — latest-wins snapshot (pub, DROP)."""
    return key(prefix(realm, flow), "state")


def result(realm: str, flow: str) -> str:
    """``{realm}/task/{flow}/result`` — terminal aggregate (pub, DROP)."""
    return key(prefix(realm, flow), "result")


def alive(realm: str, flow: str) -> str:
    return key(prefix(realm, flow), "alive")


def cmd_start(realm: str, flow: str) -> str:
    """``{realm}/task/{flow}/cmd/start`` — queryable."""
    return key(prefix(realm, flow), "cmd", "start")


def cmd_abort(realm: str, flow: str) -> str:
    """``{realm}/task/{flow}/cmd/abort`` — queryable."""
    return key(prefix(realm, flow), "cmd", "abort")
