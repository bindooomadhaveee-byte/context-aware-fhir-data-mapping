"""Raw record -> FHIR R4 resource mappers."""
from .field_resolver import resolve
from . import terminology as term

INTERP_SYSTEM = "http://terminology.hl7.org/CodeSystem/v3-ObservationInterpretation"
INTERP_TEXT = {"H": "High", "L": "Low", "N": "Normal"}


def map_patient(record, ctx):
    al = ctx.config["field_aliases"]["patient"]
    pid = resolve(record, al["id"])
    if pid is None:
        ctx.warn("Patient record without identifier skipped")
        return None
    pid = str(pid).strip()

    given, family = resolve(record, al["given"]), resolve(record, al["family"])
    if not (given and family):
        full = resolve(record, al["fullname"])
        if full:
            if "," in full:                      # "Doe, Jane"
                family, given = [p.strip() for p in full.split(",", 1)]
            else:                                # "Jane Doe"
                parts = full.split()
                given, family = " ".join(parts[:-1]), parts[-1]

    patient = {
        "resourceType": "Patient",
        "id": pid,
        "identifier": [{"system": ctx.system_cfg.get("identifier_system", "urn:unknown"), "value": pid}],
    }
    if given or family:
        name = {"use": "official"}
        if family:
            name["family"] = family
        if given:
            name["given"] = str(given).split()
        patient["name"] = [name]

    gender = term.map_gender(resolve(record, al["gender"]), ctx)
    if gender:
        patient["gender"] = gender

    dob, _ = term.parse_date(resolve(record, al["birthdate"]), ctx)
    if dob:
        patient["birthDate"] = dob.strftime("%Y-%m-%d")

    phone = resolve(record, al["phone"])
    if phone:
        patient["telecom"] = [{"system": "phone", "value": str(phone)}]
    city = resolve(record, al["city"])
    if city:
        patient["address"] = [{"city": str(city)}]

    ctx.patients[pid] = {"gender": patient.get("gender"), "birthDate": patient.get("birthDate")}
    return patient


def map_observation(record, ctx, index=0):
    al = ctx.config["field_aliases"]["observation"]
    pid = resolve(record, al["patient_id"])
    local_code = resolve(record, al["code"])
    raw_value = resolve(record, al["value"])
    if pid is None or local_code is None or raw_value is None:
        ctx.warn(f"Observation #{index} missing patient/code/value; skipped")
        return None
    pid, local_code = str(pid).strip(), str(local_code).strip()

    # Context 1: local code -> LOINC (accept LOINC codes directly)
    loinc = ctx.config["local_codes"].get(local_code.upper(), local_code)
    if loinc not in ctx.config["loinc"]:
        ctx.warn(f"Unmapped code '{local_code}'; observation #{index} skipped")
        return None

    value = term.to_float(raw_value, ctx)
    if value is None:
        return None

    # Context 2: unit comes from the record, else from the source system's defaults
    unit = resolve(record, al["unit"]) or ctx.system_cfg.get("lab_units", {}).get(local_code.upper())
    value, unit = term.normalise_unit(loinc, value, unit, ctx)

    info = ctx.config["loinc"][loinc]
    ucum = ctx.config["ucum"].get(unit, unit)
    obs = {
        "resourceType": "Observation",
        "id": f"obs-{pid}-{loinc}-{index}",
        "status": resolve(record, al["status"]) or "final",
        "category": [{"coding": [{
            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
            "code": "laboratory"}]}],
        "code": {"coding": [{"system": "http://loinc.org", "code": loinc, "display": info["display"]}]},
        "subject": {"reference": f"Patient/{pid}"},
        "valueQuantity": {"value": value, "unit": unit, "system": "http://unitsofmeasure.org", "code": ucum},
    }

    when, has_time = term.parse_date(resolve(record, al["datetime"]), ctx)
    if when:
        obs["effectiveDateTime"] = when.strftime("%Y-%m-%dT%H:%M:%S" if has_time else "%Y-%m-%d")

    # Context 3: reference range depends on the patient's sex
    sex = ctx.patients.get(pid, {}).get("gender")
    flag, low, high = term.interpret(loinc, value, sex, ctx)
    obs["interpretation"] = [{"coding": [{"system": INTERP_SYSTEM, "code": flag,
                                          "display": INTERP_TEXT[flag]}]}]
    obs["referenceRange"] = [{"low": {"value": low, "unit": unit}, "high": {"value": high, "unit": unit}}]
    return obs
