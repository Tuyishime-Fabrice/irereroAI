"""Registry of source adapters.

python -m pipelines.registry    # list sources, expected files and target tables
"""

from pipelines.adapter import SourceAdapter
from pipelines.adapters.boundaries import Boundaries
from pipelines.adapters.census_2022 import Census2022
from pipelines.adapters.education_yearbook import EducationYearbook
from pipelines.adapters.eicv7 import Eicv7
from pipelines.adapters.lfs_2025 import Lfs2025
from pipelines.adapters.ncda_mapping import NcdaMapping
from pipelines.adapters.osm import Osm
from pipelines.adapters.rdhs_2019_gps import Rdhs2019Gps
from pipelines.adapters.rdhs_2025 import Rdhs2025
from pipelines.adapters.worldpop import WorldPop

ADAPTERS: dict[str, type[SourceAdapter[object, object]]] = {
    cls.spec.name: cls
    for cls in (
        Census2022,
        Eicv7,
        Rdhs2025,
        Rdhs2019Gps,
        Lfs2025,
        EducationYearbook,
        NcdaMapping,
        WorldPop,
        Osm,
        Boundaries,
    )
}


def main() -> None:
    for name, cls in ADAPTERS.items():
        spec = cls.spec
        print(f"{name}: {spec.title} ({spec.publisher})")
        for expected in spec.expected_files:
            print(f"  file   data/raw/{expected.pattern}  {expected.description}")
        print(f"  tables {', '.join(spec.target_tables)}")


if __name__ == "__main__":
    main()
