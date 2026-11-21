import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from mapper import MappingContext, load_config, map_observation, map_patient
from mapper.cli import run
from mapper.validator import validate


def ctx(system="hospital_a"):
    return MappingContext(load_config(), system)


def test_patient_name_formats():
    p = map_patient({"PatientID": "B1", "FullName": "Smith, Anna", "Gender": "2",
                     "BirthDate": "07-21-1990"}, ctx("hospital_b"))
    assert p["name"][0]["family"] == "Smith" and p["name"][0]["given"] == ["Anna"]
    assert p["gender"] == "female" and p["birthDate"] == "1990-07-21"


def test_date_depends_on_source_system():
    a = map_patient({"MRN": "1", "DOB": "02/11/1978"}, ctx("hospital_a"))
    assert a["birthDate"] == "1978-11-02"          # dd/mm/yyyy


def test_unit_conversion_by_source_system():
    c = ctx("hospital_b")
    obs = map_observation({"PatientID": "B1", "TestCode": "GLU", "Result": "5.4"}, c)
    assert obs["valueQuantity"]["unit"] == "mg/dL"
    assert abs(obs["valueQuantity"]["value"] - 97.29) < 0.01


def test_reference_range_depends_on_sex():
    c = ctx()
    map_patient({"MRN": "M", "Sex": "M"}, c)
    map_patient({"MRN": "F", "Sex": "F"}, c)
    rec = {"TestCode": "HGB", "Result": "12.9"}
    male = map_observation({**rec, "MRN": "M"}, c)
    female = map_observation({**rec, "MRN": "F"}, c)
    assert male["interpretation"][0]["coding"][0]["code"] == "L"
    assert female["interpretation"][0]["coding"][0]["code"] == "N"


def test_end_to_end_bundle():
    root = Path(__file__).resolve().parent.parent / "data"
    bundle, warnings, errors = run(
        [f"{root}/patients_hospital_a.csv:hospital_a", f"{root}/patients_hospital_b.csv:hospital_b"],
        [f"{root}/labs.json"], "hospital_a")
    assert bundle["resourceType"] == "Bundle" and len(bundle["entry"]) == 9
    assert not errors
    assert any("Unmapped code" in w for w in warnings)


def test_validator_flags_missing_fields():
    assert validate({"resourceType": "Observation", "id": "x"})
