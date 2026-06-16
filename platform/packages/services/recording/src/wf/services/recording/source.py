"""Log source interface + MCAP backend (design §5.7).

Decodes ONLY the 2-element CBOR envelope; the payload bytes inside come back
verbatim, exactly as captured.
"""

from __future__ import annotations

from typing import IO, Iterator, NamedTuple, Protocol

import cbor2
from mcap.exceptions import McapError
from mcap.reader import make_reader


class LogRecord(NamedTuple):
    topic: str
    payload: bytes
    attachment: bytes | None
    log_time: int
    sequence: int


class LogSource(Protocol):
    def topics(self) -> dict[str, dict[str, str]]: ...  # topic -> channel metadata

    def time_range(self) -> tuple[int, int]: ...  # (start_ns, end_ns) of messages

    def iter_records(self, start_ns: int | None = None) -> Iterator[LogRecord]: ...

    def close(self) -> None: ...


class McapSource:
    def __init__(self, path: str) -> None:
        self.path = path
        self._file: IO[bytes] = open(path, "rb")
        try:
            self._reader = make_reader(self._file)
            try:
                summary = self._reader.get_summary()
            except McapError as exc:
                raise ValueError(
                    f"no summary in {path}; recording was not stopped cleanly"
                ) from exc
            if summary is None or summary.statistics is None:
                raise ValueError(
                    f"no summary in {path}; recording was not stopped cleanly"
                )
        except ValueError:
            self._file.close()
            raise
        self._summary = summary

    def topics(self) -> dict[str, dict[str, str]]:
        return {
            ch.topic: dict(ch.metadata) for ch in self._summary.channels.values()
        }

    def time_range(self) -> tuple[int, int]:
        stats = self._summary.statistics
        return (stats.message_start_time, stats.message_end_time)

    def iter_records(self, start_ns: int | None = None) -> Iterator[LogRecord]:
        # Each iteration owns a private file handle: the replayer's playback
        # thread iterates while control handlers (seek, info) scan
        # concurrently — a shared handle's seek state would corrupt both and
        # kill the playback thread.
        with open(self.path, "rb") as file:
            reader = make_reader(file)
            for _schema, channel, message in reader.iter_messages(
                start_time=start_ns, log_time_order=True
            ):
                payload, attachment = cbor2.loads(message.data)
                yield LogRecord(
                    topic=channel.topic,
                    payload=payload,
                    attachment=attachment,
                    log_time=message.log_time,
                    sequence=message.sequence,
                )

    def close(self) -> None:
        self._file.close()
