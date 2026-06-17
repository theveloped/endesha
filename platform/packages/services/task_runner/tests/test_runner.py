"""End-to-end task_runner tests against the in-process sim realm (no mocks).

The unknown-pose rejection test stands up the config service + task_runner over
two linked peer sessions and asserts a flow naming an unknown pose is rejected
before any motion — it needs no camera and runs everywhere.

The full-stack ``demo_inspect`` e2e is retired: it stood up an in-process sim
camera (the pyrender ``camera2d_sim`` driver) to render frames, which was
replaced by the external headless-browser HAL. It is kept as a documented skip.
"""

from __future__ import annotations

import pytest

from wf.contracts.task import keys as task_keys
from wf.core.codec import decode, encode
from wf.core.testing import linked_sessions

REALM = "sim"
RID = "r1"
CID = "cam0"


def _query_ok(session, key, payload, timeout_s=5.0):
    replies = session.get(key, payload=encode(payload), timeout=timeout_s)
    for reply in replies:
        if reply.ok is not None:
            return decode(reply.ok.payload)
    return None


# ── unknown-pose rejection (no camera needed) ──────────────────────────────


def test_unknown_pose_rejected_without_motion():
    from wf.services.config.service import ConfigService
    from wf.services.task_runner.service import TaskRunnerService
    from wf.services.task_runner.spec import validate_spec

    with linked_sessions() as (sa, sb), _tmp_config(sa) as store:
        cfg = ConfigService(sa, store)
        cfg.start()
        try:
            spec = validate_spec(
                {
                    "name": "bad_flow_test",
                    "poses": ["does_not_exist"],
                    "vision": {"format": "DataMatrix", "pipeline": "x_detect"},
                    "conveyor": {"timeout_s": 0.5},
                }
            )
            svc = TaskRunnerService(sb, REALM, spec, rid=RID, cid=CID)
            svc.start()
            try:
                reply = _query_ok(
                    sb, task_keys.cmd_start(REALM, "bad_flow_test"), {}
                )
                assert reply == {
                    "ok": False,
                    "error": "unknown_pose:does_not_exist",
                }
            finally:
                svc.shutdown()
        finally:
            cfg.shutdown()


# ── full-stack inspection (retired) ────────────────────────────────────────


def test_demo_inspect_end_to_end():
    pytest.skip(
        "camera2d_sim retired; sim camera is now the external headless-browser "
        "HAL — see deploy/Dockerfile.headless",
        allow_module_level=False,
    )


# ── helpers ────────────────────────────────────────────────────────────────


import contextlib
import tempfile


@contextlib.contextmanager
def _tmp_config(session):
    from wf.services.config.store import ConfigStore

    with tempfile.TemporaryDirectory() as d:
        yield ConfigStore(d)
