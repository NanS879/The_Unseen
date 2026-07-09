"""
Persistence — save/load the entire V3 ecosystem state as JSON.

Saves: energy, behavior stats, organisms, pending seeds.
Loads: restores full state so the ecosystem continues across sessions.

Design:
    Stateless functions. No class needed — just save() and load().
    JSON format for human readability and easy debugging.
"""

import json
import os
import time
from typing import Optional

from ..config import Config


def save_state(
    filepath: str,
    energy_manager,
    behavior_analyzer,
    organism_manager,
    time_system,
) -> bool:
    """Save complete V3 state to a JSON file.

    Args:
        filepath: Path to save file.
        energy_manager: EnergyManager instance.
        behavior_analyzer: BehaviorAnalyzer instance.
        organism_manager: OrganismManager instance.
        time_system: TimeSystem instance.

    Returns:
        True if save succeeded.
    """
    data = {
        "version": 3,
        "saved_at": time.time(),
        "saved_at_iso": time.strftime("%Y-%m-%dT%H:%M:%S",
                                       time.localtime()),
        "energy": energy_manager.serialize(),
        "behavior": behavior_analyzer.serialize(),
        "ecosystem": organism_manager.serialize(),
        "time_system": time_system.serialize(),
    }

    try:
        # Write to temp file first, then rename (atomic on most OS)
        tmp = filepath + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp, filepath)
        return True
    except OSError as e:
        print(f"[Persistence] Save error: {e}")
        return False


def load_state(
    filepath: str,
) -> Optional[dict]:
    """Load V3 state from a JSON file.

    Args:
        filepath: Path to the save file.

    Returns:
        Dict with keys: energy, behavior, ecosystem, time_system.
        None if file doesn't exist or is corrupt.
    """
    if not os.path.exists(filepath):
        return None

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        version = data.get("version", 0)
        if version < 3:
            print(f"[Persistence] Old version {version}, ignoring")
            return None

        saved_at = data.get("saved_at_iso", "unknown")
        orgs = len(data.get("ecosystem", {}).get("organisms", []))
        seeds = len(data.get("ecosystem", {}).get("pending_seeds", []))
        energy = data.get("energy", {}).get("energy", 0)
        print(f"[Persistence] Loaded state from {saved_at}")
        print(f"  Energy: {energy:.1f} | Organisms: {orgs} | Pending seeds: {seeds}")

        return data
    except (json.JSONDecodeError, OSError, KeyError) as e:
        print(f"[Persistence] Load error: {e}")
        return None


def delete_state(filepath: str) -> bool:
    """Delete the save file (fresh start)."""
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except OSError:
        pass
    return False
