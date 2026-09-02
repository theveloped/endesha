"""The `program` contract key space (program-layer RFC §3.5)::

    {realm}/programs/catalog          retained: pub latest-wins + queryable Catalog
    {realm}/programs/cmd/load         envelope queryable, args LoadRequest (unit Idle/Stopped only)
    {realm}/programs/cmd/source       envelope queryable, args {name|file} -> value SourceReply
    {realm}/programs/cmd/save         envelope queryable, args SaveRequest -> value SaveReply
                                      (write + rescan; an import error rides in the entry)
    {realm}/programs/cmd/delete       envelope queryable, args {name}
    {realm}/program/log               pub (program.log() + runner notes) + queryable (last N)
    {realm}/program/state             retained: pub latest-wins + queryable ProgramState
    {realm}/program/cmd/{command}     envelope queryables, args {reason?}: start hold unhold
                                      suspend unsuspend stop abort clear reset unload
    {realm}/program/cmd/event         envelope queryable, args EventRequest (HMI/bus -> program)
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
