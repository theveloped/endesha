"""Node vocabulary: bind graph node ``type``s to :class:`Leaves` handlers.

Each handler has the :class:`~wf.services.task_runner.graph.GraphRunner`
signature ``handler(node, blackboard, graph) -> port | None`` and is the ONLY
bus-touching code the control-flow runtime drives (it calls ``Leaves.*``,
exactly as the legacy statechart does). ``build_handlers(leaves)`` returns the
``{type: handler}`` registry the runner walks.

A handler may:
- read its ``node.params`` (author-set constants) and its **data inputs** (values
  produced by upstream nodes, threaded via data edges + the blackboard),
- write its output to ``blackboard[node.id]`` for downstream data edges,
- return an exec **port** to steer control flow (``branch`` returns
  ``"true"``/``"false"``; most nodes return ``None`` -> the default port).

v1 vocabulary: ``start``/``end`` (control markers), ``move``, ``grip``,
``set_do``, ``wait_di``, ``vision.start``/``vision.stop``, ``detect``, and the
``branch`` control node. Vision-graph code nodes arrive in Increment 2.
"""

from __future__ import annotations

from .graph import Graph, Node
from .leaves import Leaves

# Node types the palette/validation know about (also the handler registry keys).
NODE_TYPES = (
    "start",
    "end",
    "move",
    "grip",
    "set_do",
    "wait_di",
    "vision.start",
    "vision.stop",
    "detect",
    "branch",
)


def _inputs(graph: Graph, node: Node, bb: dict) -> dict:
    """Collect this node's data-edge inputs, keyed by the edge's ``dst_key``.

    An upstream node's output lives at ``bb[src]``; ``src_key`` optionally
    selects a field of it when that output is a mapping.
    """
    out: dict = {}
    for edge in graph.data_edges_into(node.id):
        value = bb.get(edge.src)
        if edge.src_key is not None and isinstance(value, dict):
            value = value.get(edge.src_key)
        out[edge.dst_key or edge.src_key or edge.src] = value
    return out


def _deref(bb: dict, ref: str):
    """Resolve a ``"node"`` / ``"node.key"`` blackboard reference."""
    node, _, key = ref.partition(".")
    value = bb.get(node)
    if key and isinstance(value, dict):
        return value.get(key)
    return value


def build_handlers(leaves: Leaves) -> dict:
    """Build the ``{node_type: handler}`` registry bound to ``leaves``."""

    def _noop(node, bb, graph):
        return None

    def _move(node, bb, graph):
        p = node.params
        inputs = _inputs(graph, node, bb)
        leaves.move(
            motion=p.get("motion", "movej"),
            pose_name=p.get("pose_name"),
            pose=inputs.get("pose", p.get("pose")),
            frame=inputs.get("frame", p.get("frame")),
            q=p.get("q"),
            free=p.get("free"),
            speed=p.get("speed"),
            accel=p.get("accel"),
        )
        return None

    def _grip(node, bb, graph):
        p = node.params
        leaves.grip(action=p.get("action"), value=p.get("value"), pin=p.get("pin", 0))
        return None

    def _set_do(node, bb, graph):
        p = node.params
        bank = p.get("bank", "standard")
        pin = int(p.get("pin", 0))
        value = bool(p.get("value", False))
        if bank == "tool":
            leaves._set_tool_do(pin, value)
        else:
            leaves._set_do(pin, value)
        return None

    def _wait_di(node, bb, graph):
        p = node.params
        bb[node.id] = leaves.wait_di(
            int(p.get("pin", 0)),
            timeout_s=float(p.get("timeout_s", 5.0)),
            level=bool(p.get("level", True)),
        )
        return None

    def _vision_start(node, bb, graph):
        fmt = node.params.get("format", True)
        leaves.enable_pipeline(fmt)
        return None

    def _vision_stop(node, bb, graph):
        leaves.enable_pipeline(False)
        return None

    def _detect(node, bb, graph):
        bb[node.id] = {"detections": leaves.read_results()}
        return None

    def _branch(node, bb, graph):
        p = node.params
        inputs = _inputs(graph, node, bb)
        if "value" in inputs:
            value = inputs["value"]
        elif p.get("input"):
            value = _deref(bb, p["input"])
        else:
            value = None
        if "equals" in p:
            ok = value == p["equals"]
        else:
            ok = bool(value)
        return "true" if ok else "false"

    return {
        "start": _noop,
        "end": _noop,
        "move": _move,
        "grip": _grip,
        "set_do": _set_do,
        "wait_di": _wait_di,
        "vision.start": _vision_start,
        "vision.stop": _vision_stop,
        "detect": _detect,
        "branch": _branch,
    }
