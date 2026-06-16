"""The `supervisor` contract key space — flow orchestration (design §8, §68).

The supervisor is the sole interpreter of flows: it owns the flow inventory,
resolves each flow's contract-typed roles to concrete resources, and starts /
stops the per-flow ``task_runner`` on demand.

Master-facing keys (single node is its own master):

- ``flows_catalog``      latest-wins + queryable: the selectable flows with
  their RESOLVED role bindings and online state.
- ``flows_cmd_start``    queryable: bring a flow online (spawn its task_runner).
- ``flows_cmd_stop``     queryable: take a flow offline (reap its task_runner).
- ``flow_status``        latest-wins: a single flow's spawn/run phase.
- ``supervisor_alive``   liveliness: a node's supervisor is up.
- ``supervisor_descriptor`` latest-wins + queryable: what is up on a node.

``node`` is the node id (single-node default ``"main"``).

RESERVED — per-node spawn dispatch (distributed multi-IPC, NOT built this
slice; single node spawns locally). The future key strings are::

    {realm}/supervisor/{node}/cmd/spawn     queryable: master -> owner node
    {realm}/supervisor/{node}/cmd/stop      queryable
    {realm}/supervisor/{node}/cmd/restart   queryable
    {realm}/registry/{id}                   latest-wins: a resource descriptor
                                            carrying its owning ``node`` (HALs
                                            publish this for role->node lookup)

All keys carry the realm prefix.
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def flows_prefix(realm: str) -> str:
    return key(realm_prefix(realm), "flows")


def flows_catalog(realm: str) -> str:
    """``{realm}/flows/catalog`` — selectable flows (pub latest-wins + queryable)."""
    return key(flows_prefix(realm), "catalog")


def flows_cmd_start(realm: str) -> str:
    """``{realm}/flows/cmd/start`` — bring a flow online (queryable)."""
    return key(flows_prefix(realm), "cmd", "start")


def flows_cmd_stop(realm: str) -> str:
    """``{realm}/flows/cmd/stop`` — take a flow offline (queryable)."""
    return key(flows_prefix(realm), "cmd", "stop")


def flow_status(realm: str, flow: str) -> str:
    """``{realm}/flows/{flow}/status`` — one flow's phase (pub latest-wins)."""
    return key(flows_prefix(realm), flow, "status")


def supervisor_prefix(realm: str, node: str) -> str:
    return key(realm_prefix(realm), "supervisor", node)


def supervisor_alive(realm: str, node: str = "main") -> str:
    """``{realm}/supervisor/{node}/alive`` — liveliness token."""
    return key(supervisor_prefix(realm, node), "alive")


def supervisor_descriptor(realm: str, node: str = "main") -> str:
    """``{realm}/supervisor/{node}/descriptor`` — node state (pub + queryable)."""
    return key(supervisor_prefix(realm, node), "descriptor")
