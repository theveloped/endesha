"""wiregen: deterministic generation + drift gate."""

from __future__ import annotations

from wf.tools import wiregen


def test_generation_is_deterministic_and_complete():
    keys1, keys2 = wiregen.gen_keys(), wiregen.gen_keys()
    types1, types2 = wiregen.gen_types(), wiregen.gen_types()
    assert keys1 == keys2 and types1 == types2
    # every key module rendered at least its alive/cmd surface
    for sentinel in (
        "armStateJoints", "camera2dProducerRender", "controlCmdAcquire",
        "dioCmdSet", "programCmd", "supervisorLogGlob", "tagsCmdWrite",
        "washerCmdSetRecipe", "configTcp", "recordingReplayClock",
    ):
        assert f"export function {sentinel}(" in keys1, sentinel
    # constrained + sanitized specials rendered as templates
    assert "`${realm}/program/cmd/${command}`" in keys1
    assert 'service.replace(/[/*$?#:]/g, ".")' in keys1
    # types: wire names, timestamps, floats, reasons, codes
    assert "export interface ChannelsState {" in types1
    assert "t: WireTimestamp;" in types1
    assert "  do: number;" in types1  # IoState do_ -> wire "do"
    assert "ARM_ERROR_REASONS" in types1 and "CODES" in types1
    assert "FLOAT_FIELDS" in types1 and "FrameHeader" in types1


def test_committed_output_matches(tmp_path):
    # the drift gate itself: committed files equal a fresh generation
    assert wiregen.main(["--check"]) == 0
    # and a stale copy is caught
    out = tmp_path / "gen"
    assert wiregen.main(["--out", str(out)]) == 0
    (out / "keys.ts").write_text("// stale", encoding="utf-8")
    assert wiregen.main(["--out", str(out), "--check"]) == 1
