"""The `dio` contract key space (program-layer RFC §2.2, wire-contract RFC)::

    {realm}/dio/{rid}/state/channels   retained: pub latest-wins (on change +
                                       1 Hz keepalive) + queryable answering
                                       the identical payload
    {realm}/dio/{rid}/cmd/set          envelope queryable, args SetChannel
                                       (outputs only)
    {realm}/dio/{rid}/cmd/force        envelope queryable, args ForceChannel
                                       (any channel)
    {realm}/dio/{rid}/alive            liveliness token

``cmd/*`` requests/replies are the wire-contract envelope
(``wf.core.envelope``): the acting ``client_id`` travels top-level in the
request. ``set`` and forcing an OUTPUT are guarded by the cell-level control
lease (``wf.contracts.control``). Forcing an INPUT is ungated (flagged test
override, works while a program holds the lease).
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
