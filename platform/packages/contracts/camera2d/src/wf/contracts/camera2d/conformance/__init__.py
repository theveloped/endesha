"""Bus-level conformance suite for any `camera2d` contract implementation.

Runs purely over the bus (design §2.1). All tests skip unless env
``WF_CONF_CONNECT`` (a zenoh endpoint, e.g. ``tcp/127.0.0.1:7447``) is set.

Environment:
- ``WF_CONF_CONNECT`` — required; zenoh connect endpoint.
- ``WF_CONF_REALM`` — realm (default ``live``).
- ``WF_CONF_CID`` — camera id (default ``cam0``).
"""
