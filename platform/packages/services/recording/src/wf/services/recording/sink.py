"""Log sink interface + MCAP backend (design §5.6).

MCAP layout: one channel per recorded zenoh key (channel ``topic`` = full
original key), ``message_encoding="cbor"``, message ``data`` = CBOR envelope
``[payload: bytes, attachment: bytes | None]``. Payload bytes inside the
envelope are VERBATIM — never decoded or re-encoded.
"""

from __future__ import annotations

from typing import IO, Protocol

import cbor2
from mcap.writer import CompressionType, Writer

from .keys import MARKS_TOPIC

SCHEMA_NAME = "wf.recording.envelope.v1"
_SCHEMA_DATA = (
    b"cbor array [payload: bytes, attachment: bytes | null]; "
    b"payload is the verbatim zenoh payload"
)
_LIBRARY = "wf-recording 0.1.0"


class LogSink(Protocol):
    path: str

    def write(
        self, topic: str, payload: bytes, attachment: bytes | None, recv_ns: int
    ) -> None: ...

    def write_mark(self, label: str, t_ns: int) -> None: ...

    def close(self) -> None: ...


class McapSink:
    """Single-writer-thread MCAP sink. Not thread-safe by contract."""

    def __init__(self, path: str, realm: str) -> None:
        self.path = path
        self.realm = realm
        self.message_count = 0
        self._file: IO[bytes] = open(path, "wb")
        self._writer = Writer(self._file, compression=CompressionType.NONE)
        self._writer.start(profile="", library=_LIBRARY)
        self._schema_id = self._writer.register_schema(
            name=SCHEMA_NAME, encoding="", data=_SCHEMA_DATA
        )
        self._channels: dict[str, int] = {}  # topic -> channel_id
        self._sequences: dict[int, int] = {}  # channel_id -> next sequence

    def _channel_id(self, topic: str) -> int:
        channel_id = self._channels.get(topic)
        if channel_id is None:
            channel_id = self._writer.register_channel(
                topic=topic,
                message_encoding="cbor",
                schema_id=self._schema_id,
                metadata={"realm": self.realm},
            )
            self._channels[topic] = channel_id
            self._sequences[channel_id] = 0
        return channel_id

    def write(
        self, topic: str, payload: bytes, attachment: bytes | None, recv_ns: int
    ) -> None:
        channel_id = self._channel_id(topic)
        sequence = self._sequences[channel_id]
        self._sequences[channel_id] = sequence + 1
        self._writer.add_message(
            channel_id=channel_id,
            log_time=recv_ns,
            publish_time=recv_ns,
            sequence=sequence,
            data=cbor2.dumps([payload, attachment]),
        )
        self.message_count += 1

    def write_mark(self, label: str, t_ns: int) -> None:
        self.write(MARKS_TOPIC, cbor2.dumps({"t": t_ns, "label": label}), None, t_ns)

    def close(self) -> None:
        self._writer.finish()
        self._file.close()
