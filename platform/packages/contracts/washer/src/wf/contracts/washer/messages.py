"""washer contract wire messages.

Phase model (derived by the HAL from the machine's status lines)::

    initializing     no valid status yet (PLC not connected / not in auto)
    ready_to_load    door closed, machine idle, will open for loading
    door_open        door open, basket accessible (load side)
    door_moving      door travelling (open/close in progress or stopped mid-way)
    washing          door closed, cycle running
    ready_to_unload  cycle done, door closed, will open for unloading
    fault            machine reports a general fault (``fault_code`` if known)

``sequence`` names the handshake the HAL is currently driving (an action in
flight): ``open_door`` / ``close_door`` / ``start_wash`` / ``reset`` or None.
"""

from __future__ import annotations

from dataclasses import dataclass, field

PHASES = (
    "initializing",
    "ready_to_load",
    "door_open",
    "door_moving",
    "washing",
    "ready_to_unload",
    "fault",
)

DOOR_STATES = ("open", "closed", "moving", "unknown")


@dataclass
class WasherStatus:
    t: int
    phase: str = "initializing"
    door: str = "unknown"
    connected: bool = False  # transport to the machine controller is up
    auto: bool = False  # machine in automatic (remote) mode
    fault: bool = False
    fault_code: int = 0
    washing: bool = False
    ready_to_load: bool = False
    ready_to_unload: bool = False
    program: str = ""  # name of the wash program loaded on the machine
    program_no: int = 0  # selected wash program number (0 = unknown / n/a)
    sequence: str | None = None
    detail: str = ""  # human hint: what the HAL is waiting for

    def to_wire(self) -> dict:
        return {
            "t": int(self.t),
            "phase": self.phase,
            "door": self.door,
            "connected": bool(self.connected),
            "auto": bool(self.auto),
            "fault": bool(self.fault),
            "fault_code": int(self.fault_code),
            "washing": bool(self.washing),
            "ready_to_load": bool(self.ready_to_load),
            "ready_to_unload": bool(self.ready_to_unload),
            "program": self.program,
            "program_no": int(self.program_no),
            "sequence": self.sequence,
            "detail": self.detail,
        }

    @classmethod
    def from_wire(cls, d: dict) -> "WasherStatus":
        return cls(
            t=int(d["t"]),
            phase=str(d.get("phase", "initializing")),
            door=str(d.get("door", "unknown")),
            connected=bool(d.get("connected", False)),
            auto=bool(d.get("auto", False)),
            fault=bool(d.get("fault", False)),
            fault_code=int(d.get("fault_code", 0) or 0),
            washing=bool(d.get("washing", False)),
            ready_to_load=bool(d.get("ready_to_load", False)),
            ready_to_unload=bool(d.get("ready_to_unload", False)),
            program=str(d.get("program", "") or ""),
            program_no=int(d.get("program_no", 0) or 0),
            sequence=d.get("sequence"),
            detail=str(d.get("detail", "") or ""),
        )


# ── recipes (wash programs) ──────────────────────────────────────────────────


@dataclass
class RecipeStep:
    """One step of a wash program (Ecoclean ``Programmfolgen[i]``)."""

    cleaning: int = 0  # treatment id (0 = step unused)
    time_s: int = 0
    movement: int = 0  # part movement id
    additional: int = 0  # additional treatment id
    pump_off: bool = False

    def to_wire(self) -> dict:
        return {
            "cleaning": int(self.cleaning),
            "time_s": int(self.time_s),
            "movement": int(self.movement),
            "additional": int(self.additional),
            "pump_off": bool(self.pump_off),
        }

    @classmethod
    def from_wire(cls, d: dict) -> "RecipeStep":
        return cls(
            cleaning=int(d.get("cleaning", 0) or 0),
            time_s=int(d.get("time_s", 0) or 0),
            movement=int(d.get("movement", 0) or 0),
            additional=int(d.get("additional", 0) or 0),
            pump_off=bool(d.get("pump_off", False)),
        )


@dataclass
class Recipe:
    """``name`` + ordered steps + machine parameters (``params`` keyed by the
    device's parameter names, e.g. ``swing_angle``; see :class:`RecipeSchema`
    for what a device offers)."""

    name: str = ""
    steps: list[RecipeStep] = field(default_factory=list)
    params: dict[str, int] = field(default_factory=dict)

    def to_wire(self) -> dict:
        return {
            "name": self.name,
            "steps": [s.to_wire() for s in self.steps],
            "params": {k: int(v) for k, v in self.params.items()},
        }

    @classmethod
    def from_wire(cls, d: dict) -> "Recipe":
        steps = d.get("steps") or []
        if not isinstance(steps, list):
            raise ValueError("bad_recipe:steps must be a list")
        params = d.get("params") or {}
        if not isinstance(params, dict):
            raise ValueError("bad_recipe:params must be a mapping")
        return cls(
            name=str(d.get("name", "") or ""),
            steps=[RecipeStep.from_wire(s) for s in steps],
            params={str(k): int(v) for k, v in params.items()},
        )


@dataclass
class ParamSpec:
    """Range/choices for one recipe field (UI + validation)."""

    title: str = ""
    min: int | None = None
    max: int | None = None
    choices: list[int] | None = None
    unit: str | None = None

    def to_wire(self) -> dict:
        d: dict = {"title": self.title}
        if self.min is not None:
            d["min"] = int(self.min)
        if self.max is not None:
            d["max"] = int(self.max)
        if self.choices is not None:
            d["choices"] = [int(c) for c in self.choices]
        if self.unit is not None:
            d["unit"] = self.unit
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "ParamSpec":
        return cls(
            title=str(d.get("title", "") or ""),
            min=d.get("min"),
            max=d.get("max"),
            choices=list(d["choices"]) if d.get("choices") is not None else None,
            unit=d.get("unit"),
        )

    def check(self, name: str, value) -> str | None:
        """None when ``value`` is acceptable, else a reason."""
        if isinstance(value, bool) or not isinstance(value, int):
            return f"bad_recipe:{name} must be an int"
        if self.choices is not None and value not in self.choices:
            return f"bad_recipe:{name} must be one of {self.choices}"
        if self.min is not None and value < self.min:
            return f"bad_recipe:{name} < {self.min}"
        if self.max is not None and value > self.max:
            return f"bad_recipe:{name} > {self.max}"
        return None


@dataclass
class RecipeSchema:
    """What a washer's recipes look like: how many steps, the per-step field
    specs and the machine parameter specs (returned with ``get_recipe``)."""

    steps: int = 0
    step_fields: dict[str, ParamSpec] = field(default_factory=dict)
    params: dict[str, ParamSpec] = field(default_factory=dict)

    def to_wire(self) -> dict:
        return {
            "steps": int(self.steps),
            "step_fields": {k: v.to_wire() for k, v in self.step_fields.items()},
            "params": {k: v.to_wire() for k, v in self.params.items()},
        }

    @classmethod
    def from_wire(cls, d: dict) -> "RecipeSchema":
        return cls(
            steps=int(d.get("steps", 0) or 0),
            step_fields={k: ParamSpec.from_wire(v) for k, v in (d.get("step_fields") or {}).items()},
            params={k: ParamSpec.from_wire(v) for k, v in (d.get("params") or {}).items()},
        )

    def validate(self, recipe: Recipe) -> str | None:
        if len(recipe.steps) > self.steps:
            return f"bad_recipe:at most {self.steps} steps"
        for i, step in enumerate(recipe.steps):
            for fname, spec in self.step_fields.items():
                value = getattr(step, fname)
                if fname == "pump_off":
                    if not isinstance(value, bool):
                        return f"bad_recipe:steps[{i}].pump_off must be a bool"
                    continue
                err = spec.check(f"steps[{i}].{fname}", value)
                if err is not None:
                    return err
        for pname, value in recipe.params.items():
            spec = self.params.get(pname)
            if spec is None:
                return f"bad_recipe:unknown param {pname}"
            err = spec.check(pname, value)
            if err is not None:
                return err
        return None


@dataclass
class RecipeReply:
    ok: bool
    error: str | None = None
    recipe: Recipe | None = None
    schema: RecipeSchema | None = None

    def to_wire(self) -> dict:
        d: dict = {"ok": bool(self.ok), "error": self.error}
        if self.recipe is not None:
            d["recipe"] = self.recipe.to_wire()
        if self.schema is not None:
            d["schema"] = self.schema.to_wire()
        return d

    @classmethod
    def from_wire(cls, d: dict) -> "RecipeReply":
        return cls(
            ok=bool(d.get("ok", False)),
            error=d.get("error"),
            recipe=Recipe.from_wire(d["recipe"]) if d.get("recipe") is not None else None,
            schema=RecipeSchema.from_wire(d["schema"]) if d.get("schema") is not None else None,
        )


@dataclass
class SetRecipe:
    client_id: str
    recipe: Recipe

    def to_wire(self) -> dict:
        return {"client_id": self.client_id, "recipe": self.recipe.to_wire()}

    @classmethod
    def from_wire(cls, d: dict) -> "SetRecipe":
        return cls(client_id=d["client_id"], recipe=Recipe.from_wire(d["recipe"]))


@dataclass
class Ack:
    ok: bool
    error: str | None = None

    def to_wire(self) -> dict:
        return {"ok": bool(self.ok), "error": self.error}

    @classmethod
    def from_wire(cls, d: dict) -> "Ack":
        return cls(ok=bool(d.get("ok", False)), error=d.get("error"))
