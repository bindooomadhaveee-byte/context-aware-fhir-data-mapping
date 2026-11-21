"""Lightweight structural checks (not a replacement for a full FHIR validator)."""

REQUIRED = {
    "Patient": ["id", "identifier"],
    "Observation": ["status", "code", "subject", "valueQuantity"],
}


def validate(resource):
    errors = []
    rtype = resource.get("resourceType")
    if rtype not in REQUIRED:
        return [f"Unsupported resourceType: {rtype}"]
    for key in REQUIRED[rtype]:
        if key not in resource:
            errors.append(f"{rtype}/{resource.get('id', '?')}: missing '{key}'")
    if rtype == "Patient" and resource.get("gender") not in (None, "male", "female", "other", "unknown"):
        errors.append(f"Patient/{resource['id']}: invalid gender")
    if rtype == "Observation" and resource.get("status") not in (
            "registered", "preliminary", "final", "amended", "corrected", "cancelled",
            "entered-in-error", "unknown"):
        errors.append(f"Observation/{resource['id']}: invalid status")
    return errors
