"""Terminology helpers: gender, dates, units and reference ranges."""
from datetime import datetime

FALLBACK_FORMATS = ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M", "%d/%m/%Y", "%m-%d-%Y"]


def map_gender(raw, ctx):
    if raw is None:
        return None
    result = ctx.config["gender_map"].get(str(raw).strip().lower())
    if result is None:
        ctx.warn(f"Unknown gender value '{raw}', using 'unknown'")
        return "unknown"
    return result


def parse_date(raw, ctx):
    """Return (datetime, has_time). Source-system formats are tried first (context)."""
    if raw is None:
        return None, False
    text = str(raw).strip()
    formats = ctx.system_cfg.get("date_formats", []) + FALLBACK_FORMATS
    for fmt in formats:
        try:
            return datetime.strptime(text, fmt), ("%H" in fmt)
        except ValueError:
            continue
    ctx.warn(f"Could not parse date '{raw}'")
    return None, False


def to_float(raw, ctx):
    try:
        return float(str(raw).replace(",", "."))
    except (TypeError, ValueError):
        ctx.warn(f"Non-numeric value '{raw}'")
        return None


def normalise_unit(loinc_code, value, unit, ctx):
    """Convert value into the canonical unit of the LOINC code, if a conversion exists."""
    target = ctx.config["loinc"][loinc_code]["unit"]
    if unit is None or unit == target or unit == _alt(target):
        return value, target
    factor = ctx.config["conversions"].get(loinc_code, {}).get(unit)
    if factor is None:
        ctx.warn(f"No conversion from '{unit}' to '{target}' for {loinc_code}; kept as is")
        return value, unit
    return round(value * factor, 2), target


def _alt(unit):
    return "mmHg" if unit == "mm[Hg]" else unit


def interpret(loinc_code, value, patient_gender, ctx):
    """Context-aware reference range: depends on the patient's sex when available."""
    ranges = ctx.config["loinc"][loinc_code]["ranges"]
    low, high = ranges.get(patient_gender or "", ranges["default"])
    if value < low:
        flag = "L"
    elif value > high:
        flag = "H"
    else:
        flag = "N"
    return flag, low, high
