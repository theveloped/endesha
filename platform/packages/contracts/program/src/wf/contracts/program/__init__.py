"""WF platform L1 `program` contract: the cell's program unit.

One runner per cell hosts ONE unit (PackML state machine) that loads and
executes ONE program at a time. Programs are code (``wf.program`` StateCharts);
the unit machine (Idle/Execute/Held/Aborted/…) lives in the runner and is what
operators and HMIs command.
"""
