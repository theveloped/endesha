"""The `dio` contract key space (program-layer RFC §2.2)::

    {realm}/dio/{rid}/state/channels   pub latest-wins, on change + 1 Hz keepalive
    {realm}/dio/{rid}/cmd/set          queryable SetChannel   -> Ack  (outputs only)
    {realm}/dio/{rid}/cmd/force        queryable ForceChannel -> Ack  (any channel)
    {realm}/dio/{rid}/alive            liveliness token

``set`` and ``force`` are guarded by the cell-level control lease
(``wf.contracts.control``); requests carry the ``client_id`` that must hold it.
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str, rid: str) -> str:
    return key(realm_prefix(realm), "dio", rid)


def state_channels(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "channels")


def cmd_set(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "set")


def cmd_force(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "force")


def alive(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "alive")
