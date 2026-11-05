"""Persistent Kill Switch Management.
Stores system emergency halt state on disk. Fails closed (blocks trades) if state cannot be verified.
"""

from pathlib import Path
from datetime import datetime
import json
import logging
from typing import Dict, Any, Optional

from trader.domain.models import IST

logger = logging.getLogger(__name__)
DEFAULT_KILL_SWITCH_PATH = Path("config/kill_switch.state")


class PersistentKillSwitch:
    """Manages persistent kill switch state."""

    def __init__(self, state_file: Optional[Path] = None):
        self.state_file = Path(state_file) if state_file else DEFAULT_KILL_SWITCH_PATH
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._save_state({
                "active": True,
                "reason": "Kill-switch state missing at initialization (Fail-Closed)",
                "updated_at": datetime.now(IST).isoformat(),
            })

    def _read_state(self) -> Dict[str, Any]:
        try:
            if not self.state_file.exists():
                return {"active": True, "reason": "Kill switch file missing (Fail-Closed)"}
            content = self.state_file.read_text(encoding="utf-8").strip()
            if not content:
                return {"active": True, "reason": "Empty kill switch file (Fail-Closed)"}
            return json.loads(content)
        except Exception as e:
            logger.error(f"Error reading kill switch state: {e}. Failing closed.")
            return {"active": True, "reason": f"Corrupt kill switch state: {e} (Fail-Closed)"}

    def _save_state(self, state: Dict[str, Any]) -> None:
        temp_file = self.state_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        temp_file.replace(self.state_file)

    def is_active(self) -> bool:
        """Returns True if the kill switch is currently engaged."""
        state = self._read_state()
        return bool(state.get("active", True))

    def get_reason(self) -> str:
        state = self._read_state()
        return str(state.get("reason", "Unknown reason"))

    def activate(self, reason: str = "Manual activation") -> None:
        """Engages the kill switch to halt all trading."""
        state = {
            "active": True,
            "reason": reason,
            "updated_at": datetime.now(IST).isoformat(),
        }
        self._save_state(state)
        logger.warning(f"KILL SWITCH ENGAGED: {reason}")

    def deactivate(self, reason: str = "Manual override reset") -> None:
        """Disengages the kill switch after operator confirmation."""
        state = {
            "active": False,
            "reason": reason,
            "updated_at": datetime.now(IST).isoformat(),
        }
        self._save_state(state)
        logger.info(f"KILL SWITCH DISENGAGED: {reason}")
