"""WF platform L1 `dio` contract: named digital/analog IO channels.

A dio device is any bundle of inputs/outputs — the arm's onboard IO bank, an
external IO module, later a fieldbus slice. Programs and the UI address
channels ONLY by name; the address (bank/pin/index) lives in cell.yaml and is
the provider's business. ``force`` (PLC semantics) overrides a channel's
reported value regardless of the source, which is what makes a fully
simulated device meaningful: ``sim_dio`` is a device where nothing is wired.
"""
