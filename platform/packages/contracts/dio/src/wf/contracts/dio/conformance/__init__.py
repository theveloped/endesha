"""Bus-level conformance suite for any `dio` contract implementation.

Runs purely over the bus. All tests skip unless env ``WF_CONF_CONNECT`` (a
zenoh endpoint, e.g. ``tcp/127.0.0.1:7447``) is set.

Environment:
- ``WF_CONF_CONNECT`` — required; zenoh connect endpoint.
- ``WF_CONF_REALM`` — realm (default ``cell``).
- ``WF_CONF_DIO`` — dio resource id (default ``io0``).
- ``WF_CONF_DIO_INPUT`` — a digital INPUT channel name to force (default: the
  first ``di`` in the state).
- ``WF_CONF_DIO_OUTPUT`` — a digital OUTPUT channel safe to toggle (skipped
  when unset — on live hardware only YOU know which output is harmless).

The suite acquires the cell control lease under its own client id and releases
it afterwards.
"""
