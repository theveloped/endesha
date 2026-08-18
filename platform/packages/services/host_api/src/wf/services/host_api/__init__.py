"""Host API: cell registry + supervisor lifecycle."""

from .app import create_app
from .cells import CellInfo, scan_cells
from .manager import SupervisorManager

__all__ = ["create_app", "CellInfo", "scan_cells", "SupervisorManager"]
