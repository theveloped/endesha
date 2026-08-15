"""SDK exceptions."""

from __future__ import annotations


class ProgramError(Exception):
    """A device call failed (rejected goal, timeout, unknown pose, …). Raised
    inside an action; the runner turns it into a unit Abort with the message
    as reason."""


class ActionCancelled(Exception):
    """The running action was cancelled (state exited, Hold, Stop, Abort). Raised
    from :meth:`ActionContext.check` and from any blocking proxy call; actions
    normally let it propagate."""
