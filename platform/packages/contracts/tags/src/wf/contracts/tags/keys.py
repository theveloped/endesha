"""The `tags` contract key space (wire-contract RFC)::

    {realm}/tags/{rid}/state/tags     retained: pub latest-wins (on change +
                                      1 Hz keepalive) + queryable answering
                                      the identical payload
    {realm}/tags/{rid}/cmd/write      envelope queryable, args WriteTag
                                      (rw tags only; lease-gated)
    {realm}/tags/{rid}/cmd/force     envelope queryable, args ForceTag
                                      (any tag; rw tags lease-gated)
    {realm}/tags/{rid}/alive          liveliness token

``cmd/*`` requests/replies are the wire-contract envelope
(``wf.core.envelope``); the acting ``client_id`` travels top-level.
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str, rid: str) -> str:
    return key(realm_prefix(realm), "tags", rid)


def state_tags(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "tags")


def cmd_write(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "write")


def cmd_force(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "force")


def alive(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "alive")
