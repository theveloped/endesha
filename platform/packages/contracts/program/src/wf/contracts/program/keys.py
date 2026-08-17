"""The `program` contract key space (program-layer RFC §3.5)::

    {realm}/programs/catalog          pub latest-wins + queryable  Catalog
    {realm}/programs/cmd/load         queryable LoadRequest -> Ack   (unit Idle/Stopped only)
    {realm}/programs/cmd/source       queryable {name|path} -> SourceReply   (read a program file)
    {realm}/programs/cmd/save         queryable SaveRequest -> SaveReply     (write + rescan; import error reported)
    {realm}/programs/cmd/delete       queryable {name} -> Ack               (delete a program file)
    {realm}/program/log               pub (program.log() + runner notes) + queryable (last N)
    {realm}/program/state             pub latest-wins + queryable  ProgramState
    {realm}/program/cmd/{command}     queryables -> Ack: start hold unhold suspend
                                      unsuspend stop abort clear reset unload
    {realm}/program/cmd/event         queryable EventRequest -> Ack  (HMI/bus -> program)
    {realm}/program/transitions       pub (event log, DROP)  TransitionEvent
    {realm}/program/alive             liveliness token of the runner
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix

UNIT_COMMANDS = (
    "start",
    "hold",
    "unhold",
    "suspend",
    "unsuspend",
    "stop",
    "abort",
    "clear",
    "reset",
    "unload",
)


def catalog(realm: str) -> str:
    return key(realm_prefix(realm), "programs", "catalog")


def cmd_load(realm: str) -> str:
    return key(realm_prefix(realm), "programs", "cmd", "load")


def cmd_source(realm: str) -> str:
    return key(realm_prefix(realm), "programs", "cmd", "source")


def cmd_save(realm: str) -> str:
    return key(realm_prefix(realm), "programs", "cmd", "save")


def cmd_delete(realm: str) -> str:
    return key(realm_prefix(realm), "programs", "cmd", "delete")


def prefix(realm: str) -> str:
    return key(realm_prefix(realm), "program")


def log(realm: str) -> str:
    return key(prefix(realm), "log")


def state(realm: str) -> str:
    return key(prefix(realm), "state")


def cmd(realm: str, command: str) -> str:
    if command not in UNIT_COMMANDS:
        raise ValueError(f"unknown unit command {command!r}")
    return key(prefix(realm), "cmd", command)


def cmd_glob(realm: str) -> str:
    return key(prefix(realm), "cmd", "*")


def cmd_event(realm: str) -> str:
    return key(prefix(realm), "cmd", "event")


def transitions(realm: str) -> str:
    return key(prefix(realm), "transitions")


def alive(realm: str) -> str:
    return key(prefix(realm), "alive")
