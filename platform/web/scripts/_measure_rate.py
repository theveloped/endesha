import json
import sys
import time

import zenoh

from wf.contracts.camera2d import keys
from wf.core.codec import encode

cid = sys.argv[1] if len(sys.argv) > 1 else "camZ"
c = zenoh.Config()
c.insert_json5("mode", json.dumps("peer"))
c.insert_json5("connect/endpoints", json.dumps(["tcp/127.0.0.1:7447"]))
s = zenoh.open(c)
time.sleep(0.5)

frames = []
sub = s.declare_subscriber(keys.image("sim", cid), lambda smp: frames.append(time.monotonic()))

list(
    s.get(
        keys.cmd_stream_start("sim", cid),
        payload=encode({"rate_hz": 15, "scale": 0.25, "encoding": "jpeg"}),
        timeout=5.0,
    )
)
time.sleep(4)
list(s.get(keys.cmd_stream_stop("sim", cid), payload=encode({}), timeout=5.0))
sub.undeclare()
s.close()

n = len(frames)
span = (frames[-1] - frames[0]) if n > 1 else 0
hz = (n - 1) / span if span > 0 else 0
print(f"frames={n} span={span:.2f}s achieved_hz={hz:.2f}")
