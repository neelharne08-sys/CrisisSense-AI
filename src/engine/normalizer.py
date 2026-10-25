import copy
from typing import Dict, List, Optional, Tuple, Set, Any
import numpy as np
from src.schemas import StreamEvent, SourceType

class Checkpoint:
    """Snapshot of engine state at minute t for rewind and replay."""
    def __init__(self, minute: int, belief: np.ndarray, ledger: List[StreamEvent], 
                 retracted_ids: Set[str], fatigue: float, action: str):
        self.minute = minute
        self.belief = belief.copy()
        self.ledger = [copy.deepcopy(e) for e in ledger]
        self.retracted_ids = set(retracted_ids)
        self.fatigue = fatigue
        self.action = action

class StreamNormalizer:
    """
    Fixed-lag 15-minute replay buffer, exact/fuzzy deduplicator,
    retraction handler, and cutout detector.
    """
    def __init__(self, buffer_minutes: int = 15):
        self.buffer_minutes = buffer_minutes
        self.checkpoints: Dict[int, Checkpoint] = {}
        self.events_by_id: Dict[str, StreamEvent] = {}
        self.fuzzy_seen: Dict[Tuple[str, str, str], int] = {} # (source_type, location, kind) -> event_time
        self.claim_seen: Dict[str, str] = {} # claim_id -> first event id
        self.retracted_ids: Set[str] = {} if False else set()
        self.active_cutouts: Set[str] = set()

    def add_checkpoint(self, minute: int, belief: np.ndarray, ledger: List[StreamEvent], 
                       fatigue: float, action: str):
        self.checkpoints[minute] = Checkpoint(
            minute=minute,
            belief=belief,
            ledger=ledger,
            retracted_ids=self.retracted_ids,
            fatigue=fatigue,
            action=action
        )
        # Prune older than buffer_minutes
        min_retained = minute - self.buffer_minutes
        for m in list(self.checkpoints.keys()):
            if m < min_retained:
                del self.checkpoints[m]

    def get_checkpoint(self, minute: int) -> Optional[Checkpoint]:
        return self.checkpoints.get(minute)

    def is_exact_duplicate(self, event: StreamEvent) -> bool:
        if event.id in self.events_by_id:
            return True
        if event.dup_of and event.dup_of in self.events_by_id:
            return True
        return False

    def is_fuzzy_duplicate(self, event: StreamEvent) -> bool:
        # If marked as duplicate of another event
        if event.dup_of is not None:
            return True

        # Check multiple transmissions from the same sensor in the same minute
        current_min = event.event_time // 60
        key = (event.source_id, event.source_type.value, event.location, event.kind.value, current_min)
        if key in self.fuzzy_seen:
            return True
        self.fuzzy_seen[key] = event.event_time
        return False

    def register_event(self, event: StreamEvent):
        self.events_by_id[event.id] = event

    def register_retraction(self, target_id: str):
        self.retracted_ids.add(target_id)

    def is_retracted(self, event_id: str) -> bool:
        return event_id in self.retracted_ids

    def set_cutout(self, source_type: str, active: bool = True):
        if active:
            self.active_cutouts.add(source_type)
        else:
            self.active_cutouts.discard(source_type)

    def get_blind_sources(self) -> List[str]:
        return sorted(list(self.active_cutouts))
