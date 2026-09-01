# ADR-0011 — This framework is never the safety controller

Date: 2026-06 (design v5 §1, permanent non-goal) · Status: accepted, permanent

## Decision

Safety-rated functions (e-stop circuits, protective stops, enabling devices,
safeguarded space) live in the robot controller and safety PLC/hardware —
never in Zenoh, Python, or React. The UI may *request* motion; the driver
enforces lease, watchdog, speed clamp and mode checks; the safety chain
remains physical and certified. The bus *reports* safety state, it never
implements it.

Also permanent: no hard real-time servo control from the PC (the vendor
controller closes the servo loop).

## Validate new plans against

Does any part of the plan make software on the bus responsible for
preventing harm (interlocks, safe zones, speed supervision)? Then the plan
is mis-scoped: the bus may *mirror* and *visualize* that state only.
