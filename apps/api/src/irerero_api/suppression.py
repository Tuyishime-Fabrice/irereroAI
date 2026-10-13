"""Small-count suppression for public pages and exports: any count below 5 is withheld."""

from irerero_api.schemas.common import PublicCount

THRESHOLD = 5


def suppress(value: int | float | None) -> PublicCount:
    if value is None:
        return PublicCount(value=None, suppressed=False)
    rounded = round(value)
    if 0 < rounded < THRESHOLD:
        return PublicCount(value=None, suppressed=True)
    return PublicCount(value=rounded, suppressed=False)


def suppress_csv(value: int | float | None) -> str:
    count = suppress(value)
    if count.suppressed:
        return "<5"
    return "" if count.value is None else str(count.value)
