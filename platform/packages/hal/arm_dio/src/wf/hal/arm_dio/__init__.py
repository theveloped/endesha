"""``arm_dio``: a dio provider fronting an arm's onboard IO bank (RFC §2.3)."""

from .backend import ArmDioBackend

__all__ = ["ArmDioBackend"]
