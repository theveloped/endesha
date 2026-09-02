"""The `washer` contract key space (an industrial parts washer with a load
door and a wash cycle — Ecoclean class machines)::

    {realm}/washer/{rid}/state/status        pub latest-wins, on change + 1 Hz (+ queryable) WasherStatus
    {realm}/washer/{rid}/action/open_door    action  {client_id}            -> door open (load or unload side)
    {realm}/washer/{rid}/action/close_door   action  {client_id}            -> door closed, no wash
    {realm}/washer/{rid}/action/start_wash   action  {client_id, program?}  -> door closed + cycle started
    {realm}/washer/{rid}/action/reset        action  {client_id}            -> handshake lines cleared, faults acknowledged
    {realm}/washer/{rid}/action/cancel       action cancel (a moving door stops: permission released)
    {realm}/washer/{rid}/cmd/stop_door       envelope queryable, args {}   -> value {} (immediate: release permission; lease-gated)
    {realm}/washer/{rid}/cmd/get_recipe      envelope queryable, args {}   -> value RecipeReply {recipe, schema?}
    {realm}/washer/{rid}/cmd/set_recipe      envelope queryable, args SetRecipe {recipe} (lease-gated; invalid:bad_recipe, busy:washing)
    {realm}/washer/{rid}/alive               liveliness token

Actions are goals (they take seconds: door travel, handshakes) so a program's
cancel stops the door; ``start_wash`` succeeds when the machine confirms the
door closed and the cycle running — the wash itself is observed on
``state/status`` (phase ``washing`` -> ``ready_to_unload``).
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix

ACTIONS = ("open_door", "close_door", "start_wash", "reset")


def prefix(realm: str, rid: str) -> str:
    return key(realm_prefix(realm), "washer", rid)


def state_status(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "state", "status")


def action_prefix(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "action")


def cmd_stop_door(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "stop_door")


def cmd_get_recipe(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "get_recipe")


def cmd_set_recipe(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "cmd", "set_recipe")


def alive(realm: str, rid: str) -> str:
    return key(prefix(realm, rid), "alive")
