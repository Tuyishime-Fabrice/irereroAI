"""Every dataset IrereroAI uses, in the order of the brief. Drives DATA_SOURCES.md and the
source table."""

from irerero.config import OBSERVED, PUBLISHED, SIMULATED
from irerero.data.sources import boundaries, census, eicv, ncda, osm, projections, rdhs, worldpop
from irerero.data.sources import yearbook as yearbook_source
from irerero.data.spec import Dataset

STANDARDS_DATASET = Dataset(
    key="ecd_standards",
    title="National ECD Standards (2024)",
    publisher="National Child Development Agency (NCDA)",
    files=(),
    format="Parameters in irerero/config.py, each cited",
    columns=(),
    level="national",
    reference_period="2024",
    licence="Government publication; cited",
    url="https://www.ncda.gov.rw",
    used_by=("PLAN: 30 children per room, 1 caregiver per 15 to 30 children, 1 km walk",),
    status=PUBLISHED,
    fallback="Not a file: the parameters are always present",
)
COURSES_DATASET = Dataset(
    key="courses",
    title="Course source materials (NCDA, UNICEF, WHO)",
    publisher="NCDA, UNICEF, WHO",
    files=(),
    format="Markdown lessons and JSON quizzes in content/courses/, each citing its source",
    columns=(),
    level="course",
    reference_period="as cited",
    licence="Adapted from public materials, cited in each course",
    url=None,
    used_by=("LEARN: the four courses",),
    status=OBSERVED,
    fallback="Lesson text is marked placeholder until the team finalises it",
)
LEARN_SIMULATION = Dataset(
    key="learn_simulation",
    title="Simulated check-ins and course progress, Muhanga",
    publisher="IrereroAI demo generator (seed 2026)",
    files=(),
    format="Generated at first start into the app tables",
    columns=(),
    level="centre",
    reference_period="2026",
    licence="Simulated; no real people",
    url=None,
    used_by=("LEARN: demo caregivers, check-ins, triggers and progress",),
    status=SIMULATED,
    fallback="Always simulated: plants no water, few meal days and an attendance drop",
)

DATASETS: tuple[Dataset, ...] = (
    census.DATASET,
    worldpop.DATASET,
    projections.DATASET,
    boundaries.DATASET,
    osm.DATASET,
    yearbook_source.DATASET,
    rdhs.DATASET,
    eicv.DATASET,
    STANDARDS_DATASET,
    COURSES_DATASET,
    ncda.DATASET,
    LEARN_SIMULATION,
)
FILE_DATASETS = tuple(d for d in DATASETS if d.files)
