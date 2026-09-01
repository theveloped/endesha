"""Bus-level conformance suite for the `control` contract (the cell lease).

Runs purely over the bus against a live authority. All tests skip unless env
``WF_CONF_CONNECT`` (a zenoh endpoint, e.g. ``tcp/127.0.0.1:7447``) is set.

Environment:
- ``WF_CONF_CONNECT`` — required; zenoh connect endpoint.
- ``WF_CONF_REALM`` — realm (default ``cell``).

The suite acquires and releases the lease under throwaway client ids; it
skips (rather than fights) when another client already holds the lease.
"""
