import json
import sys
import time

import zenoh

from wf.contracts.camera2d import keys
from wf.core.codec import encode

cid = sys.argv[1] if len(sys.argv) > 1 else "camVerify"
c = zenoh.Config()
c.insert_json5("mode", json.dumps("peer"))
c.insert_json5("connect/endpoints", json.dumps(["tcp/127.0.0.1:7447"]))
s = zenoh.open(c)
time.sleep(0.5)
got = []
sub = s.declare_subscriber(keys.image("sim", cid), lambda smp: got.append(smp.payload.to_bytes()))
list(s.get(keys.cmd_stream_start("sim", cid), payload=encode({"rate_hz": 10, "scale": 0.25, "encoding": "jpeg"}), timeout=5.0))
time.sleep(1.5)
list(s.get(keys.cmd_stream_stop("sim", cid), payload=encode({}), timeout=5.0))
sub.undeclare()
s.close()
if got:
    with open("web/cam_frame.jpg", "wb") as fh:
        fh.write(got[-1])
    print("wrote web/cam_frame.jpg", len(got[-1]), "bytes")
else:
    print("no frames")
