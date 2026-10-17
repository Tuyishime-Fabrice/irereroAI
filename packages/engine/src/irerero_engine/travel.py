"""Walking time from a place to many others: along roads and paths, or estimated in a line.

The build precomputes catchments with one of these and stores the minutes, so the planner's
map and the optimizer never route at request time.

Phase 1 fallback: straight-line distance times a detour factor, at an adjustable walking speed.
With the OpenStreetMap extract loaded: shortest paths over walkable ways, plus a straight walk
(with the same detour factor) from each place to its nearest way.
"""

import heapq
import math
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from typing import Protocol

from irerero_engine.types import Position

DEFAULT_METRES_PER_MINUTE = 67.0  # about 4 km/h on rural paths
# Paths wind; rural studies put walking distance 1.2 to 1.4 times the straight line.
DEFAULT_DETOUR = 1.3
SNAP_CELL_METRES = 250.0


class TravelTimes(Protocol):
    method: str

    def minutes(
        self, origin: Position, targets: Sequence[Position], limit: float
    ) -> list[float | None]:
        """Walking minutes to each target, or None beyond `limit` minutes."""
        ...


class StraightLineTravel:
    method = "straight_line"

    def __init__(
        self,
        metres_per_minute: float = DEFAULT_METRES_PER_MINUTE,
        detour: float = DEFAULT_DETOUR,
    ) -> None:
        self.metres_per_minute = metres_per_minute
        self.detour = detour

    def between(self, a: Position, b: Position) -> float:
        return a.distance_to(b) * self.detour / self.metres_per_minute

    def minutes(
        self, origin: Position, targets: Sequence[Position], limit: float
    ) -> list[float | None]:
        out: list[float | None] = []
        for target in targets:
            walk = self.between(origin, target)
            out.append(walk if walk <= limit else None)
        return out


class RoadNetwork:
    """Walkable ways as a graph. Node positions are metres in EPSG:32735."""

    method = "road_network"

    def __init__(
        self,
        nodes: Mapping[int, Position],
        edges: Iterable[tuple[int, int]],
        metres_per_minute: float = DEFAULT_METRES_PER_MINUTE,
        detour: float = DEFAULT_DETOUR,
    ) -> None:
        self.nodes = dict(nodes)
        self.off_road = StraightLineTravel(metres_per_minute, detour)
        self.metres_per_minute = metres_per_minute
        self.adjacent: dict[int, list[tuple[int, float]]] = defaultdict(list)
        for a, b in edges:
            if a == b or a not in self.nodes or b not in self.nodes:
                continue
            minutes = self.nodes[a].distance_to(self.nodes[b]) / metres_per_minute
            self.adjacent[a].append((b, minutes))
            self.adjacent[b].append((a, minutes))
        self.grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for node_id in self.adjacent:
            self.grid[self._cell(self.nodes[node_id])].append(node_id)

    @staticmethod
    def _cell(p: Position) -> tuple[int, int]:
        return math.floor(p.x / SNAP_CELL_METRES), math.floor(p.y / SNAP_CELL_METRES)

    def nearest_node(self, p: Position) -> int | None:
        """The closest connected node, searching outward ring by ring."""
        cx, cy = self._cell(p)
        best: tuple[float, int] | None = None
        for ring in range(0, 41):
            for dx in range(-ring, ring + 1):
                for dy in range(-ring, ring + 1):
                    if max(abs(dx), abs(dy)) != ring:
                        continue
                    for node_id in self.grid.get((cx + dx, cy + dy), ()):
                        d = self.nodes[node_id].distance_to(p)
                        if best is None or d < best[0]:
                            best = (d, node_id)
            # Anything in a further ring is at least `ring` cells away.
            if best is not None and best[0] <= ring * SNAP_CELL_METRES:
                return best[1]
        return best[1] if best else None

    def _shortest(self, start: int, limit: float) -> dict[int, float]:
        done: dict[int, float] = {}
        queue = [(0.0, start)]
        while queue:
            minutes, node = heapq.heappop(queue)
            if node in done:
                continue
            done[node] = minutes
            for neighbour, cost in self.adjacent[node]:
                total = minutes + cost
                if total <= limit and neighbour not in done:
                    heapq.heappush(queue, (total, neighbour))
        return done

    def minutes(
        self, origin: Position, targets: Sequence[Position], limit: float
    ) -> list[float | None]:
        start = self.nearest_node(origin)
        if start is None:
            return self.off_road.minutes(origin, targets, limit)
        access = self.off_road.between(origin, self.nodes[start])
        reached = self._shortest(start, max(0.0, limit - access))
        out: list[float | None] = []
        for target in targets:
            direct = self.off_road.between(origin, target)
            best = direct if direct <= limit else None
            node = self.nearest_node(target)
            if node is not None and node in reached:
                total = access + reached[node] + self.off_road.between(self.nodes[node], target)
                if total <= limit and (best is None or total < best):
                    best = total
            out.append(best)
        return out
