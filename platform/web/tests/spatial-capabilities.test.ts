import assert from "node:assert/strict";
import test from "node:test";
import { commandCapabilities } from "../src/spatial/capabilities.ts";
import type { ArmStatus } from "../src/lib/messages.ts";

const nominalStatus: ArmStatus = {
  t: 0,
  mode: "manual",
  servo_on: true,
  estop: false,
  protective_stop: false,
  speed_scale: 0.2,
  active_tcp: "flange",
  error: null,
  state_rate_hz: 200,
};

test("replay always disables commands", () => {
  const capabilities = commandCapabilities({
    mode: "teach",
    replay: true,
    connected: true,
    driverAlive: true,
    holdsControl: true,
    status: nominalStatus,
  });
  assert.equal(capabilities.inspect, true);
  assert.equal(capabilities.jog, false);
  assert.equal(capabilities.motion, false);
  assert.equal(capabilities.ioWrite, false);
});

test("teach mode with control enables motion and jog", () => {
  const capabilities = commandCapabilities({
    mode: "teach",
    replay: false,
    connected: true,
    driverAlive: true,
    holdsControl: true,
    status: nominalStatus,
  });
  assert.equal(capabilities.jog, true);
  assert.equal(capabilities.motion, true);
  assert.equal(capabilities.ioWrite, true);
  assert.equal(capabilities.reason, null);
});

test("protective stop removes all actuation capability", () => {
  const capabilities = commandCapabilities({
    mode: "teach",
    replay: false,
    connected: true,
    driverAlive: true,
    holdsControl: true,
    status: { ...nominalStatus, protective_stop: true },
  });
  assert.equal(capabilities.jog, false);
  assert.equal(capabilities.motion, false);
  assert.equal(capabilities.ioWrite, false);
  assert.match(capabilities.reason ?? "", /Protective stop/);
});

test("lease loss disables motion while retaining inspection", () => {
  const capabilities = commandCapabilities({
    mode: "teach",
    replay: false,
    connected: true,
    driverAlive: true,
    holdsControl: false,
    status: nominalStatus,
  });
  assert.equal(capabilities.inspect, true);
  assert.equal(capabilities.jog, false);
  assert.equal(capabilities.motion, false);
  assert.match(capabilities.reason ?? "", /Acquire control/);
});

test("observe mode never exposes robot motion", () => {
  const capabilities = commandCapabilities({
    mode: "observe",
    replay: false,
    connected: true,
    driverAlive: true,
    holdsControl: true,
    status: nominalStatus,
  });
  assert.equal(capabilities.jog, false);
  assert.equal(capabilities.motion, false);
  assert.match(capabilities.reason ?? "", /Teach mode/);
});
