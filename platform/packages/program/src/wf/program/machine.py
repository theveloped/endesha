"""The ``Machine`` facade: the cell's devices, by id and by role.

Built from the supervisor's device inventory (``[{id, contract, …}]``). A
program declares ``roles = {"arm": "arm", "io": "dio"}`` (role -> contract);
the runner binds roles to device ids and hands the program a :class:`Roles`
view so it can write ``self.m.arm.move_j(...)`` and ``self.m.io.wait(...)``.
Role names in :data:`RESERVED_ROLE_NAMES` are rejected at bind time.
"""

from __future__ import annotations

import threading

from .errors import ProgramError
from .proxies import PROXIES, ArmProxy, DeviceProxy, make_pose_resolver


# Names a program's ``self.m`` uses for helpers; not usable as role names
# (a real attribute wins over ``__getattr__``, so the role would be unreachable).
RESERVED_ROLE_NAMES = frozenset({"bindings", "machine", "pose", "device", "ids", "rid"})


class Machine:
    def __init__(self, session, realm: str, client_id: str, devices: list[dict], *,
                 program_name: str | None = None):
        self.session = session
        self.realm = realm
        self.client_id = client_id
        self.devices = {d["id"]: dict(d) for d in devices}
        self._program_name = program_name
        self._lock = threading.Lock()
        self._proxies: dict[str, DeviceProxy] = {}
        self._pose_resolver = make_pose_resolver(session, program_name)

    # ── devices ──────────────────────────────────────────────────────────

    def ids(self, contract: str | None = None) -> list[str]:
        return [
            rid for rid, d in self.devices.items() if contract is None or d.get("contract") == contract
        ]

    def device(self, rid: str) -> DeviceProxy:
        with self._lock:
            proxy = self._proxies.get(rid)
            if proxy is not None:
                return proxy
            entry = self.devices.get(rid)
            if entry is None:
                raise ProgramError(f"unknown_device:{rid}")
            contract = entry.get("contract")
            cls = PROXIES.get(contract)
            if cls is None:
                raise ProgramError(f"no_proxy_for_contract:{contract}")
            if cls is ArmProxy:
                proxy = ArmProxy(self.session, self.realm, rid, self.client_id, pose_resolver=self._pose_resolver)
            else:
                proxy = cls(self.session, self.realm, rid, self.client_id)
            proxy.start()
            self._proxies[rid] = proxy
            return proxy

    def arm(self, rid: str) -> ArmProxy:
        proxy = self.device(rid)
        if not isinstance(proxy, ArmProxy):
            raise ProgramError(f"not_an_arm:{rid}")
        return proxy

    def dio(self, rid: str):
        proxy = self.device(rid)
        if proxy.contract != "dio":
            raise ProgramError(f"not_a_dio:{rid}")
        return proxy

    def tags(self, rid: str):
        proxy = self.device(rid)
        if proxy.contract != "tags":
            raise ProgramError(f"not_a_tags_device:{rid}")
        return proxy

    def washer(self, rid: str):
        proxy = self.device(rid)
        if proxy.contract != "washer":
            raise ProgramError(f"not_a_washer:{rid}")
        return proxy

    def pose(self, name: str) -> list[float]:
        return self._pose_resolver(name)

    # ── roles ────────────────────────────────────────────────────────────

    def resolve_bindings(self, roles: dict[str, str], bindings: dict[str, str]) -> dict[str, str]:
        """Complete ``bindings`` (role -> rid): an unbound role defaults to the
        sole device of its contract; ambiguity or a contract mismatch raises."""
        out: dict[str, str] = {}
        for role, contract in roles.items():
            if role in RESERVED_ROLE_NAMES or role.startswith("_"):
                raise ProgramError(f"bind:{role}:reserved_role_name")
            rid = bindings.get(role)
            if rid is None:
                candidates = self.ids(contract)
                if len(candidates) == 1:
                    rid = candidates[0]
                elif not candidates:
                    raise ProgramError(f"bind:{role}:no_device_of_contract:{contract}")
                else:
                    raise ProgramError(f"bind:{role}:ambiguous:{','.join(candidates)}")
            entry = self.devices.get(rid)
            if entry is None:
                raise ProgramError(f"bind:{role}:unknown_device:{rid}")
            if entry.get("contract") != contract:
                raise ProgramError(f"bind:{role}:contract_mismatch:{rid}:{entry.get('contract')}!={contract}")
            out[role] = rid
        return out

    def bind(self, roles: dict[str, str], bindings: dict[str, str]) -> "Roles":
        return Roles(self, self.resolve_bindings(roles, bindings))

    def close(self) -> None:
        with self._lock:
            proxies = list(self._proxies.values())
            self._proxies.clear()
        for p in proxies:
            try:
                p.close()
            except Exception:
                pass


class Roles:
    """What a program sees as ``self.m``: the bound roles as attributes
    (``self.m.arm``, ``self.m.io``) plus the cell-level helpers a program may
    need (``pose``, ``device``, ``ids``, ``bindings``, ``machine``, ``rid``).
    Those names are reserved as role names (see :data:`RESERVED_ROLE_NAMES`)."""

    def __init__(self, machine: Machine, bindings: dict[str, str]):
        self._machine = machine
        self._bindings = dict(bindings)

    @property
    def bindings(self) -> dict[str, str]:
        return dict(self._bindings)

    @property
    def machine(self) -> Machine:
        """The underlying cell facade (all devices, not just the bound roles)."""
        return self._machine

    def pose(self, name: str) -> list[float]:
        """Resolve a named pose (program-scoped first, then cell-wide)."""
        return self._machine.pose(name)

    def device(self, rid: str):
        """A device proxy by device id (outside the role bindings)."""
        return self._machine.device(rid)

    def ids(self, contract: str | None = None) -> list[str]:
        """Device ids in the cell (optionally of one contract)."""
        return self._machine.ids(contract)

    def rid(self, role: str) -> str:
        try:
            return self._bindings[role]
        except KeyError:
            raise ProgramError(f"unbound_role:{role}") from None

    def __getattr__(self, role: str):
        # Only reached for names that are not real attributes/methods above.
        if role.startswith("_"):
            raise AttributeError(role)
        return self._machine.device(self.rid(role))

    def __getitem__(self, role: str):
        return self._machine.device(self.rid(role))
