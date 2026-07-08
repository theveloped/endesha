"""Node-graph doc model + control-flow interpreter (design: node-graph authoring).

A *graph doc* is the operator-authored, cell-agnostic definition of a **skill**
or a **flow**: a set of typed ``nodes`` wired by ``edges``. Two edge kinds:

- **exec** edges (``from -> to``, optional ``port``) define control flow — the
  order nodes run in, including branches (a node emits a port; the matching exec
  edge is followed).
- **data** edges (``from: node.key -> to: node.key``) pass a value produced by an
  upstream node into a downstream node's input, threaded through a blackboard.

``load_graph``/``validate_graph`` parse + shape-check a doc into a :class:`Graph`
(violations raise ``ValueError("bad_graph:<reason>")``, mirroring the config
store's ``bad_*:`` convention). :class:`GraphRunner` walks the exec edges from
the entry node, invoking a registered handler per node type and threading a
shared blackboard; it is deliberately **bus-agnostic** — handlers (see
``nodes.py``) hold the only zenoh-touching code, exactly as ``leaves.py`` is the
only bus-touching code the legacy statechart drives.

This runs the NEW graph-doc flows; the legacy ``demo_inspect`` parallel
statechart keeps running on ``flow.py`` untouched (parallel regions are a later
increment). ``is_graph_doc`` lets a loader tell the two formats apart.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# The default exec output port a node follows when its handler returns no
# explicit port. A branch node returns e.g. "true"/"false" instead.
DEFAULT_PORT = "out"

_KINDS = ("flow", "skill")


def _fail(reason: str) -> "ValueError":
    return ValueError(f"bad_graph:{reason}")


class GraphError(Exception):
    """A graph interpreter runtime failure (missing handler, bad wiring)."""


class Aborted(Exception):
    """The run was aborted between nodes (raised by :meth:`GraphRunner.run`)."""


@dataclass(frozen=True)
class Node:
    """One graph node: a stable ``id``, a ``type`` (handler key), and params."""

    id: str
    type: str
    params: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Edge:
    """A wire between two nodes.

    ``kind`` is ``"exec"`` (control flow: follow ``src`` port ``port`` to
    ``dst``) or ``"data"`` (pass ``src``'s output key ``src_key`` into ``dst``'s
    input key ``dst_key``).
    """

    src: str
    dst: str
    kind: str = "exec"
    port: str = DEFAULT_PORT
    src_key: str | None = None
    dst_key: str | None = None


@dataclass
class Graph:
    name: str
    kind: str
    roles: dict
    nodes: dict[str, Node]
    edges: list[Edge]
    start: str

    def data_edges_into(self, node_id: str) -> list[Edge]:
        """Data edges whose ``dst`` is ``node_id`` (upstream inputs)."""
        return [e for e in self.edges if e.kind == "data" and e.dst == node_id]

    def exec_edges_from(self, node_id: str) -> list[Edge]:
        return [e for e in self.edges if e.kind == "exec" and e.src == node_id]


def is_graph_doc(raw: object) -> bool:
    """True when a parsed doc is a node-graph (has ``nodes``), not a legacy spec."""
    return isinstance(raw, dict) and "nodes" in raw


def load_graph(path: str | Path) -> Graph:
    """Load + validate a graph YAML file into a :class:`Graph`."""
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    return validate_graph(raw)


def _validate_name(name: object) -> str:
    if not isinstance(name, str) or not name:
        raise _fail("name must be a non-empty string")
    if any(c.isspace() for c in name) or "/" in name:
        raise _fail("name must not contain whitespace or '/'")
    return name


def _validate_roles(roles_in: object) -> dict:
    if roles_in is None:
        return {"arm": {"contract": "arm"}, "cam": {"contract": "camera2d"}}
    if not isinstance(roles_in, dict) or not roles_in:
        raise _fail("roles must be a non-empty mapping")
    roles: dict = {}
    for role_name, decl in roles_in.items():
        if not isinstance(role_name, str) or not role_name:
            raise _fail("roles_must_be_named")
        if not isinstance(decl, dict):
            raise _fail(f"roles.{role_name}_must_be_a_mapping")
        contract = decl.get("contract")
        if not isinstance(contract, str) or not contract:
            raise _fail(f"roles.{role_name}.contract_must_be_a_string")
        roles[role_name] = {"contract": contract}
    return roles


def _parse_node(raw: object) -> Node:
    if not isinstance(raw, dict):
        raise _fail("each node must be a mapping")
    nid = raw.get("id")
    if not isinstance(nid, str) or not nid:
        raise _fail("node id must be a non-empty string")
    ntype = raw.get("type")
    if not isinstance(ntype, str) or not ntype:
        raise _fail(f"node {nid}.type must be a non-empty string")
    params = raw.get("params") or {}
    if not isinstance(params, dict):
        raise _fail(f"node {nid}.params must be a mapping")
    return Node(id=nid, type=ntype, params=dict(params))


def _parse_endpoint(value: object, side: str) -> tuple[str, str | None]:
    """Split an edge endpoint ``"node"`` or ``"node.key"`` into ``(node, key)``."""
    if not isinstance(value, str) or not value:
        raise _fail(f"edge {side} must be a non-empty string")
    node, _, key = value.partition(".")
    if not node:
        raise _fail(f"edge {side} must name a node")
    return node, (key or None)


def _parse_edge(raw: object, node_ids: set[str]) -> Edge:
    if not isinstance(raw, dict):
        raise _fail("each edge must be a mapping")
    src, src_key = _parse_endpoint(raw.get("from"), "from")
    dst, dst_key = _parse_endpoint(raw.get("to"), "to")
    if src not in node_ids:
        raise _fail(f"edge from unknown node {src!r}")
    if dst not in node_ids:
        raise _fail(f"edge to unknown node {dst!r}")
    kind = raw.get("kind", "exec")
    if kind not in ("exec", "data"):
        raise _fail(f"edge kind must be 'exec' or 'data', got {kind!r}")
    if kind == "data":
        return Edge(src=src, dst=dst, kind="data", src_key=src_key, dst_key=dst_key)
    port = raw.get("port", DEFAULT_PORT)
    if not isinstance(port, str) or not port:
        raise _fail(f"edge {src}->{dst} port must be a non-empty string")
    return Edge(src=src, dst=dst, kind="exec", port=port)


def _resolve_start(raw: dict, nodes: dict[str, Node], edges: list[Edge]) -> str:
    """Pick the entry node: explicit ``start:`` wins, else a sole ``type: start``
    node, else the unique node with no incoming exec edge."""
    explicit = raw.get("start")
    if explicit is not None:
        if explicit not in nodes:
            raise _fail(f"start names unknown node {explicit!r}")
        return explicit
    typed = [n.id for n in nodes.values() if n.type == "start"]
    if len(typed) == 1:
        return typed[0]
    if len(typed) > 1:
        raise _fail("multiple 'start' nodes; set an explicit start:")
    has_incoming = {e.dst for e in edges if e.kind == "exec"}
    roots = [nid for nid in nodes if nid not in has_incoming]
    if len(roots) == 1:
        return roots[0]
    raise _fail("cannot determine start node; set an explicit start:")


def validate_graph(raw: object) -> Graph:
    """Validate an already-parsed mapping into a :class:`Graph`."""
    if not isinstance(raw, dict):
        raise _fail("root must be a mapping")

    name = _validate_name(raw.get("name"))
    kind = raw.get("kind", "flow")
    if kind not in _KINDS:
        raise _fail(f"kind must be one of {_KINDS}")
    roles = _validate_roles(raw.get("roles"))

    nodes_in = raw.get("nodes")
    if not isinstance(nodes_in, list) or not nodes_in:
        raise _fail("nodes must be a non-empty list")
    nodes: dict[str, Node] = {}
    for raw_node in nodes_in:
        node = _parse_node(raw_node)
        if node.id in nodes:
            raise _fail(f"duplicate node id {node.id!r}")
        nodes[node.id] = node

    edges_in = raw.get("edges") or []
    if not isinstance(edges_in, list):
        raise _fail("edges must be a list")
    node_ids = set(nodes)
    edges = [_parse_edge(e, node_ids) for e in edges_in]

    start = _resolve_start(raw, nodes, edges)
    return Graph(
        name=name, kind=kind, roles=roles, nodes=nodes, edges=edges, start=start
    )


class GraphRunner:
    """Walks a :class:`Graph`'s exec edges, running one handler per node.

    ``handlers`` maps a node ``type`` to ``handler(node, blackboard, graph)``,
    which performs the node's work and returns the exec **port** to follow
    (``None`` -> :data:`DEFAULT_PORT`). A node with no matching outgoing exec
    edge for the returned port is terminal (the run ends).

    ``on_node(node_id)`` is called as each node is entered (the service uses it
    to publish the live active node). ``is_aborted()`` is polled between nodes;
    when true the run raises :class:`Aborted`. ``max_steps`` guards against a
    cyclic graph running forever (loops are a later increment).
    """

    def __init__(
        self,
        graph: Graph,
        handlers: dict,
        *,
        on_node=None,
        is_aborted=None,
        max_steps: int = 10_000,
    ) -> None:
        self.graph = graph
        self.handlers = handlers
        self._on_node = on_node
        self._is_aborted = is_aborted or (lambda: False)
        self.max_steps = max_steps
        self.trace: list[str] = []

    def run(self, blackboard: dict | None = None) -> dict:
        bb = blackboard if blackboard is not None else {}
        node_id: str | None = self.graph.start
        steps = 0
        while node_id is not None:
            if self._is_aborted():
                raise Aborted("aborted")
            steps += 1
            if steps > self.max_steps:
                raise GraphError("step_limit_exceeded")
            node = self.graph.nodes[node_id]
            self.trace.append(node_id)
            if self._on_node is not None:
                self._on_node(node_id)
            handler = self.handlers.get(node.type)
            if handler is None:
                raise GraphError(f"no_handler:{node.type}")
            port = handler(node, bb, self.graph) or DEFAULT_PORT
            node_id = self._next(node_id, port)
        return bb

    def _next(self, node_id: str, port: str) -> str | None:
        outs = [e for e in self.graph.exec_edges_from(node_id) if e.port == port]
        if not outs:
            return None
        if len(outs) > 1:
            raise GraphError(f"ambiguous_exec:{node_id}:{port}")
        return outs[0].dst
