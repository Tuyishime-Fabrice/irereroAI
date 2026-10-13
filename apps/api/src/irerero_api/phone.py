import re

RWANDA_MOBILE = re.compile(r"^\+2507\d{8}$")


def normalise_phone(raw: str) -> str | None:
    """Return the E.164 form of a Rwandan mobile number, or None if it is not one."""
    digits = re.sub(r"[\s\-()]", "", raw)
    if digits.startswith("07") and len(digits) == 10:
        digits = "+250" + digits[1:]
    elif digits.startswith("2507"):
        digits = "+" + digits
    return digits if RWANDA_MOBILE.match(digits) else None
