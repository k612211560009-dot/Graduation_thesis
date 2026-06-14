from __future__ import annotations
import json, logging
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

logger = logging.getLogger(__name__)


class EventStreamProcessor:
    def __init__(self, ocel_path: str | Path) -> None:
        self.ocel_path = Path(ocel_path)
        self._events: List[Dict] = []
        self._obj_map: Dict[str, Dict] = {}   # id → object dict

    # public
    def load(self) -> "EventStreamProcessor":
        if not self.ocel_path.exists():
            raise FileNotFoundError(self.ocel_path)
        with self.ocel_path.open(encoding="utf-8") as f:
            raw = json.load(f)

        self._obj_map = {o["id"]: o for o in raw.get("objects", [])}
        # Sort events by time
        self._events = sorted(raw.get("events", []), key=lambda e: e.get("time",""))
        logger.info("OCEL loaded: %d events, %d objects", len(self._events), len(self._obj_map))
        return self

    def events_as_list(self) -> List[Dict]:
        return list(self._events)

    def get_object(self, oid: str) -> Optional[Dict]:
        return self._obj_map.get(oid)

    def get_obj_attr(self, oid: str, attr_name: str) -> Optional[Any]:
        obj = self._obj_map.get(oid)
        if not obj:
            return None
        for a in obj.get("attributes", []):
            if a["name"] == attr_name:
                return a["value"]
        return None

    def get_all_objects(self) -> Dict[str, Dict]:
        return self._obj_map

    @staticmethod
    def get_event_attr(event: Dict, name: str) -> Optional[Any]:
        for a in event.get("attributes", []):
            if a["name"] == name:
                return a["value"]
        return None

    @staticmethod
    def get_related_ids(event: Dict, prefix: str = None) -> List[str]:
        result = []
        for r in event.get("relationships", []):
            oid = r["objectId"]
            if prefix is None or oid.startswith(prefix):
                result.append(oid)
        return result
