"""tags contract core: :class:`TagsCore` (generic channels core + tags schema,
with inventory-based name resolution) and the :class:`TagsBackend` seam."""

from .backend import TagsBackend
from .core import TagsCore, load_tags_resource

__all__ = ["TagsBackend", "TagsCore", "load_tags_resource"]
