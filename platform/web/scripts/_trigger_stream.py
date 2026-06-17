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
list(
    s.get(
        keys.cmd_stream_start("sim", cid),
        payload=encode({"rate_hz": 10, "scale": 0.25, "encoding": "jpeg"}),
        timeout=5.0,
    )
)
print("stream started; collecting 3s")
time.sleep(3)
list(s.get(keys.cmd_stream_stop("sim", cid), payload=encode({}), timeout=5.0))
s.close()
print("done")
