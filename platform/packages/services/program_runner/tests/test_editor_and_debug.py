"""Editor endpoints (source/save/delete) + debug aids (waiting_for, log)."""

from __future__ import annotations

import time
import uuid

import pytest

from wf.contracts.control.authority import ControlAuthority
from wf.contracts.program import keys
from wf.contracts.program.messages import (
    Catalog,
    LoadRequest,
    LogLine,
    ProgramState,
    SaveReply,
    SaveRequest,
    SourceReply,
)
from wf.core.codec import decode, encode
from wf.core.envelope import request as envelope_request
from wf.services.program_runner.service import ProgramRunner

DEVICES = [{"id": "io0", "contract": "dio", "model": None, "active": "sim", "config": {"channels": {}}, "sources": []}]

GOOD = '''
from wf.program import Program, State, after, on_channel

class Blink(Program):
    program_name = "blink"
    roles = {"io": "dio"}
    triggers = [on_channel("io", "button", edge="rising", event="pressed"),
                after(60.0, state="idle", event="bored")]
    idle = State(initial=True)
    on = State()
    done = State(final=True)
    pressed = idle.to(on)
    off = on.to(idle)
    bored = idle.to(done)
    stop = on.to(done)
'''

BROKEN = "from wf.program import Program\nclass X(Program:\n"


def _q(session, key, payload=None):
    for reply in session.get(key, payload=encode(payload or {}), timeout=5.0):
        if reply.ok is not None:
            return decode(reply.ok.payload)
    pytest.fail(f"no reply from {key}")


@pytest.fixture
def runner(tmp_path):
    zenoh = pytest.importorskip("zenoh")
    session = zenoh.open(zenoh.Config())
    realm = f"t{uuid.uuid4().hex[:8]}"
    authority = ControlAuthority(session, realm, ttl_s=30.0)
    authority.start()
    programs = tmp_path / "programs"
    programs.mkdir()
    (programs / "blink.py").write_text(GOOD, encoding="utf-8")
    r = ProgramRunner(session, realm, str(programs), devices=DEVICES)
    r.start()
    time.sleep(0.2)
    yield session, realm, r, programs
    r.shutdown()
    authority.close()
    session.close()


def _cmd(session, key, args=None):
    """Envelope command; retained reads keep using _q."""
    return envelope_request(session, key, args or {}, timeout_s=5.0)


def test_source_save_delete_roundtrip(runner):
    session, realm, r, programs = runner
    r = _cmd(session, keys.cmd_source(realm), {"name": "blink"})
    assert r.ok
    src = SourceReply.from_wire(r.value)
    assert src.name == "blink" and "class Blink" in src.text and src.path.endswith("blink.py")
    r = _cmd(session, keys.cmd_source(realm), {"name": "nope"})
    assert not r.ok and r.error.reason == "unknown_program"
    # by bare file name too (a new file the catalog does not know yet)
    assert not _cmd(session, keys.cmd_source(realm), {"file": "fresh.py"}).ok

    # save a broken module: file written, catalog lists it with the error
    r = _cmd(session, keys.cmd_save(realm), SaveRequest("fresh.py", BROKEN).to_wire())
    assert r.ok
    rep = SaveReply.from_wire(r.value)
    assert rep.entry.error and "SyntaxError" in rep.entry.error
    assert (programs / "fresh.py").read_text(encoding="utf-8") == BROKEN
    cat = Catalog.from_wire(_q(session, keys.catalog(realm)))
    assert {p.name for p in cat.programs} == {"blink", "fresh"}

    # fix it: entry becomes loadable
    fixed = GOOD.replace('program_name = "blink"', 'program_name = "fresh"')
    r = _cmd(session, keys.cmd_save(realm), SaveRequest("fresh.py", fixed).to_wire())
    assert r.ok
    rep = SaveReply.from_wire(r.value)
    assert rep.entry.error is None and rep.entry.name == "fresh"
    assert _cmd(session, keys.cmd_load(realm), LoadRequest("fresh").to_wire()).ok

    # bad file names are refused; delete removes file + catalog entry
    bad = _cmd(session, keys.cmd_save(realm), SaveRequest("../x.py", "").to_wire())
    assert not bad.ok and bad.error.reason == "bad_file"
    assert _cmd(session, keys.cmd_delete(realm), {"name": "fresh"}).ok
    assert not (programs / "fresh.py").exists()
    cat = Catalog.from_wire(_q(session, keys.catalog(realm)))
    assert {p.name for p in cat.programs} == {"blink"}
    st = ProgramState.from_wire(_q(session, keys.state(realm)))
    assert st.program is None  # the deleted program was unloaded


def test_waiting_for_and_log(runner):
    session, realm, r, programs = runner
    assert _cmd(session, keys.cmd_load(realm), LoadRequest("blink").to_wire()).ok
    assert _cmd(session, keys.cmd(realm, "start")).ok
    deadline = time.monotonic() + 10
    st = None
    while time.monotonic() < deadline:
        st = ProgramState.from_wire(_q(session, keys.state(realm)))
        if st.unit == "execute":
            break
        time.sleep(0.05)
    assert st is not None and st.unit == "execute" and st.program_states == ["idle"]
    kinds = {(w["kind"], w["event"]) for w in st.waiting_for}
    assert ("channel", "pressed") in kinds
    assert ("timer", "bored") in kinds
    ch = next(w for w in st.waiting_for if w["kind"] == "channel")
    assert ch["channel"] == "button" and ch["edge"] == "rising" and ch["target"] == "on"
    # log: the runner announced the start; the query returns the ring buffer
    lines = [LogLine.from_wire(ln) for ln in _q(session, keys.log(realm))["lines"]]
    assert any(ln.source == "runner" and ln.message.startswith("started blink") for ln in lines)
    # unit-level abort shows the reason in the log
    assert _cmd(session, keys.cmd(realm, "abort"), {"reason": "test"}).ok
    time.sleep(0.3)
    lines = [LogLine.from_wire(ln) for ln in _q(session, keys.log(realm))["lines"]]
    assert any(ln.level == "warning" and "abort" in ln.message for ln in lines)
