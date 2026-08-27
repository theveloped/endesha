"""``sim_tags``: a controller where nothing is wired — variables from a declared
inventory, driven by force or a script."""

from .backend import SimTagsBackend, parse_inventory

__all__ = ["SimTagsBackend", "parse_inventory"]
