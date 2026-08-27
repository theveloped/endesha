"""WF platform L1 `tags` contract: named, typed variables of a controller.

A tags device is what a PLC / machine controller exposes over OPC-UA, Modbus,
S7, … — variables with a type (bool/int/float/string) and access (r/rw). Like
`dio`, programs and the UI address tags ONLY by name; the address (OPC-UA
node id, register, …) lives in cell.yaml or in the provider's own inventory,
whose raw entries show up as `auto` tags with a name derived from the
controller's own display name (``ReadyToLoad`` -> ``ready_to_load``).
"""
