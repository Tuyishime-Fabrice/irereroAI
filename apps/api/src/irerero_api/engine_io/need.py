from collections.abc import Sequence

from sqlalchemy import Connection, text

from irerero_engine.need import AreaNeed
from irerero_engine.types import Driver, Range, SourceRef

QUERY = text(
    """
    SELECT DISTINCT ON (n.area_code) n.*
    FROM need_estimate n
    WHERE n.area_code = ANY(:codes)
    ORDER BY n.area_code, n.reference_year DESC
    """
)


def _range(row: object, prefix: str) -> Range:
    return Range(
        float(getattr(row, f"{prefix}_estimate")),
        float(getattr(row, f"{prefix}_low")),
        float(getattr(row, f"{prefix}_high")),
    )


def load_need(conn: Connection, codes: Sequence[str]) -> dict[str, AreaNeed]:
    result = {}
    for row in conn.execute(QUERY, {"codes": list(codes)}):
        result[row.area_code] = AreaNeed(
            area_code=row.area_code,
            children_0_2=_range(row, "children_0_2"),
            children_3_6=_range(row, "children_3_6"),
            stunting_risk=_range(row, "stunting_risk"),
            mothers_barrier_share=_range(row, "mothers_barrier_share"),
            drivers=tuple(Driver(**d) for d in row.top_drivers),
            sources=(SourceRef("need_estimate", row.source, row.reference_year, row.origin),),
            model_version=row.model_version_id,
        )
    return result
