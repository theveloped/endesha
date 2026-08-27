"""WF platform L1 `control` contract: the cell-level control lease.

One operator (client_id) holds control of ALL devices in a cell at a time. The
lease is granted by a single authority (hosted by the supervisor) and merely
*checked* by every provider before it accepts a guarded command.
"""
