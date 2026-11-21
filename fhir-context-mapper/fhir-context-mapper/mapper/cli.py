"""Command line entry point.

Example:
  python -m mapper.cli \
      --patients data/patients_hospital_a.csv:hospital_a data/patients_hospital_b.csv:hospital_b \
      --observations data/labs.json --out output/bundle.json
"""
import argparse
import csv
import json
from pathlib import Path

from .bundle import build_bundle
from .context import MappingContext, load_config
from .mappers import map_observation, map_patient
from .validator import validate


def split_spec(spec, default):
    path, _, system = spec.partition(":")
    return path, (system or default)


def read_records(path):
    if path.lower().endswith(".csv"):
        with open(path, newline="", encoding="utf-8-sig") as fh:
            return list(csv.DictReader(fh))
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def run(patient_specs, obs_specs, default_system, config_path=None):
    ctx = MappingContext(load_config(config_path), default_system)
    resources = []

    for spec in patient_specs:
        path, system = split_spec(spec, default_system)
        sctx = ctx.with_system(system)
        for rec in read_records(path):
            p = map_patient(rec, sctx)
            if p:
                resources.append(p)

    for spec in obs_specs:
        path, system = split_spec(spec, default_system)
        for i, rec in enumerate(read_records(path)):
            # A record can override the source system itself (per-record context)
            sctx = ctx.with_system(rec.get("source_system") or system)
            o = map_observation(rec, sctx, i)
            if o:
                resources.append(o)

    errors = [e for r in resources for e in validate(r)]
    return build_bundle(resources), ctx.warnings, errors


def main():
    ap = argparse.ArgumentParser(description="Context-aware FHIR data mapper")
    ap.add_argument("--patients", nargs="*", default=[], help="FILE[:SYSTEM] (csv/json)")
    ap.add_argument("--observations", nargs="*", default=[], help="FILE[:SYSTEM] (csv/json)")
    ap.add_argument("--system", default="hospital_a", help="default source system")
    ap.add_argument("--config", default=None)
    ap.add_argument("--out", default="output/bundle.json")
    args = ap.parse_args()

    bundle, warnings, errors = run(args.patients, args.observations, args.system, args.config)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    print(f"Wrote {len(bundle['entry'])} resources to {args.out}")
    for w in warnings:
        print("WARNING:", w)
    for e in errors:
        print("VALIDATION ERROR:", e)


if __name__ == "__main__":
    main()
