"""Bus-level conformance suite for any `arm` contract implementation.

Runs purely over the bus (design §2.1). All tests skip unless env
``WF_CONF_CONNECT`` (a zenoh endpoint, e.g. ``tcp/127.0.0.1:7447``) is set.

Environment:
- ``WF_CONF_CONNECT`` — required; zenoh connect endpoint.
- ``WF_CONF_REALM`` — realm (default ``live``).
- ``WF_CONF_RID`` — resource id (default ``r1``).
- ``WF_CONF_TEST_DO_PIN`` — standard DO pin for the set_do roundtrip test
  (skipped when unset).
- ``WF_CONF_ALLOW_MOTION=1`` — additionally gates the cancel/busy test,
  which moves the robot (±5 deg on wrist3).
"""
