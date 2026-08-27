"""The ``TagsBackend`` seam.

A tags backend knows the controller's own variable inventory
(:meth:`inventory`: display name, type, access, address) and moves raw values.
The core resolves cell ``tags:`` entries given by ``tag: <display name>``
against that inventory and shows the rest as ``auto`` tags.
"""

from __future__ import annotations

from abc import abstractmethod

from wf.contracts.tags.messages import TagDef
from wf.hal.channels_core import ChannelsBackend


class TagsBackend(ChannelsBackend):
    @abstractmethod
    def inventory(self) -> list[TagDef]:
        """The controller's variables: ``TagDef(name=<display name>, type,
        access, address=<provider address, e.g. {"node": "ns=4;i=85"}>)``.
        May be empty when the provider only serves explicitly addressed tags."""

    def points(self) -> list[tuple[str, dict]]:
        # Auto tags are derived from ``inventory()`` by TagsCore, not here.
        return []
