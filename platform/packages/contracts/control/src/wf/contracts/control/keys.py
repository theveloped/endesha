"""The `control` contract key space (program-layer RFC §2.4, wire-contract
RFC).

One lease per cell, so keys carry no resource id::

    {realm}/control/cmd/acquire   envelope queryable, args AcquireControl
                                  {user}; grants or renews for the request's
                                  top-level client_id -> value
                                  ControlOwnerState | conflict:held_by
    {realm}/control/cmd/release   envelope queryable, args {} -> value
                                  ControlOwnerState | conflict:not_holder
    {realm}/control/state/owner   retained: pub latest-wins + queryable
                                  answering the identical ControlOwnerState
    {realm}/control/alive         liveliness token of the authority
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str) -> str:
    return key(realm_prefix(realm), "control")


def cmd_acquire(realm: str) -> str:
    return key(prefix(realm), "cmd", "acquire")


def cmd_release(realm: str) -> str:
    return key(prefix(realm), "cmd", "release")


def state_owner(realm: str) -> str:
    return key(prefix(realm), "state", "owner")


def alive(realm: str) -> str:
    return key(prefix(realm), "alive")
