"""Every dataset IrereroAI can use, in the order DATA_SOURCES.md lists them."""

from pipelines.sources.base import Loader
from pipelines.sources.boundaries import OFFICIAL as BOUNDARIES
from pipelines.sources.census_2022 import Census2022
from pipelines.sources.covariates import Chirps, Srtm, Viirs
from pipelines.sources.ecd_centres import EcdCentres
from pipelines.sources.education_yearbook import EducationYearbook
from pipelines.sources.eicv7 import Eicv7
from pipelines.sources.facilities import HealthFacilities
from pipelines.sources.lfs_2025 import Lfs2025
from pipelines.sources.osm import Osm
from pipelines.sources.rdhs_2025 import Rdhs2025
from pipelines.sources.spec import Dataset
from pipelines.sources.worldpop import WorldPop

# Load order: centres before the tables that describe them, health facilities before OSM so
# health points are not shown twice. Boundaries load first, outside this list.
LOADERS: tuple[Loader, ...] = (
    EcdCentres(),
    Census2022(),
    Eicv7(),
    Lfs2025(),
    Rdhs2025(),
    EducationYearbook(),
    WorldPop(),
    HealthFacilities(),
    Osm(),
    Chirps(),
    Srtm(),
    Viirs(),
)

# The order of the brief: census, surveys, reports, rasters, boundaries, roads, facilities,
# covariates, centres.
DATASETS: tuple[Dataset, ...] = (
    Census2022.dataset,
    Eicv7.dataset,
    Lfs2025.dataset,
    Rdhs2025.dataset,
    EducationYearbook.dataset,
    WorldPop.dataset,
    BOUNDARIES,
    Osm.dataset,
    HealthFacilities.dataset,
    Chirps.dataset,
    Srtm.dataset,
    Viirs.dataset,
    EcdCentres.dataset,
)
