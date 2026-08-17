"""The Ecoclean PLC's OPC-UA variable inventory (namespace 4) and the recipe
(wash program) layout — ported from ``ecoclean-controller/app/static``.

Display names are the PLC's own (German where the PLC is German); they show
up as ``auto`` tags on the provided ``tags`` device (``ready_to_load``,
``programmfolgen_2_zeit``…) exactly like unmapped ``di3`` pins. Cell-level
names are given in ``cell.yaml`` ``provides.<rid>.tags``.
"""

from __future__ import annotations

from wf.contracts.washer.messages import ParamSpec, RecipeSchema

_NS = 4


def node(i: int) -> str:
    return f"ns={_NS};i={i}"


# ── machine -> us (status lines) ─────────────────────────────────────────────
STATUS_TAGS: dict[str, tuple[int, str]] = {
    "ReadyToLoad": (85, "bool"),
    "ReadyToUnload": (86, "bool"),
    "GeneralFault": (87, "bool"),
    "DoorOpen": (88, "bool"),
    "DoorClosed": (89, "bool"),
    "WashingInProgress": (90, "bool"),
    "Auto": (91, "bool"),
    "WatchDog1Hz": (92, "bool"),
    "stoernummer": (104, "int"),  # fault number
    "Spare2": (93, "bool"),
    "Spare3": (128, "bool"),
    "Spare4": (129, "bool"),
    "Spare5": (130, "bool"),
    "Spare6": (131, "bool"),
    "Spare7": (132, "bool"),
    "Spare8": (133, "bool"),
    "Spare9": (100, "bool"),
    "SpareInt0": (101, "int"),
    "SpareInt1": (135, "int"),
    "SpareInt2": (136, "int"),
}

# ── us -> machine (handshake lines) ─────────────────────────────────────────
COMMAND_TAGS: dict[str, tuple[int, str]] = {
    "LoadRequest": (118, "bool"),
    "LoadInProgress": (119, "bool"),
    "LoadComplete": (120, "bool"),
    "UnLoadRequest": (121, "bool"),
    "UnLoadInProgress": (122, "bool"),
    "UnLoadComplete": (123, "bool"),
    "PermissionToClose": (124, "bool"),
    "EmergencyStopReset": (125, "bool"),
    "WatchDogExt": (126, "bool"),
    "FaultReset": (127, "bool"),
    "WashProgram": (134, "int"),
    "ResetSignalCloseDoor": (137, "bool"),
}

HANDSHAKE_LINES = (
    "LoadRequest", "LoadInProgress", "LoadComplete",
    "UnLoadRequest", "UnLoadInProgress", "UnLoadComplete",
)

# ── recipe: 10 steps (Programmfolgen[0..9]) x 5 fields, then machine params ──
RECIPE_STEPS = 10
# field name -> (offset inside a step block, type); step k header is i=8+6k
STEP_FIELDS: dict[str, tuple[int, str]] = {
    "cleaning": (1, "int"),  # BEH
    "time_s": (2, "int"),  # ZEIT
    "movement": (3, "int"),  # WBWG
    "additional": (4, "int"),  # ZUSATZ
    "pump_off": (5, "bool"),  # ABPUMP
}
_STEP_DISPLAY = {"cleaning": "BEH", "time_s": "ZEIT", "movement": "WBWG", "additional": "ZUSATZ", "pump_off": "ABPUMP"}


def step_display(k: int, field: str) -> str:
    return f"Programmfolgen[{k}].{_STEP_DISPLAY[field]}"


def step_node(k: int, field: str) -> str:
    return node(8 + 6 * k + STEP_FIELDS[field][0])


# our name -> (display, node id, type, spec)
RECIPE_PARAMS: dict[str, tuple[str, int, str, ParamSpec]] = {
    "swing_angle": ("Schwenkwinkel", 68, "int", ParamSpec("Swing path", 10, 120, unit="deg")),
    "pause_swing_s": ("PauseSchwenk", 69, "int", ParamSpec("Pause swing", 1, 60, unit="s")),
    "interval_angle": ("Intervallwinkel", 70, "int", ParamSpec("Interval rotation path", 10, 180, unit="deg")),
    "pause_interval_s": ("Pause_Intervall", 71, "int", ParamSpec("Pause interval rotation", 1, 60, unit="s")),
    "reference_point": ("Bezugspunkt", 72, "int", ParamSpec("Swing reference point", 0, 360, unit="deg")),
    "rpm": ("UPM", 73, "int", ParamSpec("Speed", 1, 9, unit="rpm")),
    "straighten_angle": ("WinkelGerade", 74, "int", ParamSpec("Angle position during straightening", 10, 120, unit="deg")),
    "us_1kw": ("US_1KW", 75, "int", ParamSpec("US 1kW")),
    "vapor_pressure_mbar": ("DampfdruckAB", 76, "int", ParamSpec("Working tank pressure reduction vapor degreasing", 20, 95, unit="mbar")),
    "usp_hold_time_upper": ("USP_HALTEZEIT_OG", 78, "int", ParamSpec("USP hold time upper")),
    "usp_hold_time_lower": ("USP_HALTEZEIT_UG", 79, "int", ParamSpec("USP hold time lower")),
    "usp_hold_pressure": ("USP_HALTEDRUCK", 80, "int", ParamSpec("USP hold pressure")),
    "ifw_rpm": ("IFWDrehzahl", 81, "int", ParamSpec("IFW speed", 1200, 3000, unit="rpm")),
}
RECIPE_NAME_DISPLAY = "Kommentar"
RECIPE_NAME_NODE = 77

RECIPE_SCHEMA = RecipeSchema(
    steps=RECIPE_STEPS,
    step_fields={
        "cleaning": ParamSpec("Cleaning", 0, 9),
        "time_s": ParamSpec("Time", 0, 600, unit="s"),
        "movement": ParamSpec("Part movement", 0, 4),
        "additional": ParamSpec("Add. treatment", 0, 9),
        "pump_off": ParamSpec("Pump off"),
    },
    params={name: spec for name, (_d, _n, _t, spec) in RECIPE_PARAMS.items()},
)


def inventory_dict() -> dict[str, dict]:
    """The full inventory in ``sim_tags``/``opcua`` ``inventory:`` shape
    (display name -> {node, type, access})."""
    inv: dict[str, dict] = {}
    for display, (i, typ) in STATUS_TAGS.items():
        inv[display] = {"node": node(i), "type": typ, "access": "r"}
    for display, (i, typ) in COMMAND_TAGS.items():
        inv[display] = {"node": node(i), "type": typ, "access": "rw"}
    for k in range(RECIPE_STEPS):
        for field, (_off, typ) in STEP_FIELDS.items():
            inv[step_display(k, field)] = {"node": step_node(k, field), "type": typ, "access": "rw"}
    for _name, (display, i, typ, _spec) in RECIPE_PARAMS.items():
        inv[display] = {"node": node(i), "type": typ, "access": "rw"}
    inv[RECIPE_NAME_DISPLAY] = {"node": node(RECIPE_NAME_NODE), "type": "string", "access": "rw"}
    return inv
