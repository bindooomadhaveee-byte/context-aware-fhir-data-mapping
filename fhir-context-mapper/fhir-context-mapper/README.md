# Context-Aware FHIR Data Mapping

A small Python project that converts heterogeneous source data (CSV/JSON from different
hospital systems) into **FHIR R4** `Patient` and `Observation` resources, packaged as a
transaction `Bundle`. Pure standard library; `pytest` is only needed for tests.

## What "context-aware" means here
| Context | Effect on mapping |
|---|---|
| **Source system** | Date format (`dd/mm/yyyy` vs `mm-dd-yyyy`), identifier system URL, default lab units |
| **Column names** | Aliases + fuzzy matching (`DOB`, `BirthDate`, `dateOfBirth` -> `birthDate`) |
| **Name layout** | `First`/`Last` columns, `"Jane Doe"`, or `"Doe, Jane"` |
| **Lab code + unit** | Local code -> LOINC; glucose mmol/L -> mg/dL, Hb g/L -> g/dL |
| **Patient sex** | Hemoglobin reference range / High-Low-Normal interpretation |

## Project layout
```
config/mappings.json   terminology, aliases, unit conversions, per-system settings
mapper/                context, field resolver, terminology, mappers, validator, bundle, CLI
data/                  sample inputs for two hospitals
tests/                 pytest suite
output/                generated bundle.json
```

## Run
```bash
pip install -r requirements.txt
python -m mapper.cli \
  --patients data/patients_hospital_a.csv:hospital_a data/patients_hospital_b.csv:hospital_b \
  --observations data/labs.json \
  --out output/bundle.json
pytest -q
```
Each input can be `FILE:SYSTEM`; an observation record may also carry its own
`source_system` field. Unknown codes or bad values produce warnings instead of crashing.

## Extend it
- New hospital: add an entry under `systems` in `config/mappings.json`.
- New lab test: add to `local_codes`, `loinc`, and (if needed) `conversions`.
- New resource (Encounter, Condition...): add a mapper in `mapper/mappers.py` and a rule in `mapper/validator.py`.
- Push to a server: POST `output/bundle.json` to your FHIR server base URL.
