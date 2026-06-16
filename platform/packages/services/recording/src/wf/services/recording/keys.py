"""Key builders for the recording control plane and replay realms.

The recorder's own control plane is realm-less (``recording/...``) so its
traffic is never captured by the ``{realm}/**`` subscriber.
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix

RECORDING_PREFIX = "recording"
MARKS_TOPIC = "recording/marks"  # synthetic in-file topic, never a live bus key


def cmd_start() -> str:
    return key(RECORDING_PREFIX, "cmd", "start")


def cmd_stop() -> str:
    return key(RECORDING_PREFIX, "cmd", "stop")


def cmd_mark() -> str:
    return key(RECORDING_PREFIX, "cmd", "mark")


def state() -> str:
    return key(RECORDING_PREFIX, "state")


def recorder_alive() -> str:
    return key(RECORDING_PREFIX, "alive")


def replay_realm(session_id: str) -> str:
    """Validated ``replay/{session_id}`` realm prefix."""
    return realm_prefix(key("replay", session_id))


def replay_cmd(session_id: str, action: str) -> str:
    return key(replay_realm(session_id), "cmd", action)


def replay_clock(session_id: str) -> str:
    return key(replay_realm(session_id), "clock")
