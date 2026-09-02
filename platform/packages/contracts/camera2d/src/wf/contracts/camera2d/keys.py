"""The `camera2d` contract key space (design §4.1/§4.3, wire-contract RFC).

``cmd/*`` (grab / configure / stream_start / stream_stop) and the producer
election (``producer/cmd/acquire`` / ``release``) are envelope queryables
(``wf.core.envelope``). Frame-shaped exchanges are exempt from the envelope
like streams: the ``image`` topic and the per-client ``producer/.../render``
reply carry raw image bytes as the zenoh payload with a CBOR header as the
attachment.
"""

from __future__ import annotations

from wf.core.keys import key, realm_prefix


def prefix(realm: str, cid: str) -> str:
    return key(realm_prefix(realm), "camera2d", cid)


def image(realm: str, cid: str) -> str:
    """The single frame topic — stream AND grab frames publish here."""
    return key(prefix(realm, cid), "image")


def state_status(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "state", "status")


def cmd_configure(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "configure")


def cmd_grab(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "grab")


def cmd_stream_start(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "stream_start")


def cmd_stream_stop(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "cmd", "stream_stop")


def alive(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "alive")

def producer_prefix(realm: str, cid: str) -> str:
    return key(prefix(realm, cid), "producer")


def producer_cmd_acquire(realm: str, cid: str) -> str:
    return key(producer_prefix(realm, cid), "cmd", "acquire")


def producer_cmd_release(realm: str, cid: str) -> str:
    return key(producer_prefix(realm, cid), "cmd", "release")


def producer_state_owner(realm: str, cid: str) -> str:
    return key(producer_prefix(realm, cid), "state", "owner")


def producer_state_demand(realm: str, cid: str) -> str:
    return key(producer_prefix(realm, cid), "state", "demand")


def producer_ingress(realm: str, cid: str) -> str:
    return key(producer_prefix(realm, cid), "ingress")


def producer_render(realm: str, cid: str, client_id: str) -> str:
    return key(producer_prefix(realm, cid), "clients", client_id, "render")



def optical_frame(cid: str) -> str:
    """Name of the camera optical frame: ``camera2d/{cid}/optical``.

    Realm-less frame name (mirrors ``arm.keys.base_frame``); used as
    ``frame_id`` until frames v0 lands.
    """
    return key("camera2d", cid, "optical")
