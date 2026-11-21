"""Mapping context: carries source-system settings, patient info and warnings."""
import json
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_CONFIG = Path(__file__).resolve().parent.parent / "config" / "mappings.json"


def load_config(path=None):
    with open(path or DEFAULT_CONFIG, encoding="utf-8") as fh:
        return json.load(fh)


@dataclass
class MappingContext:
    config: dict
    source_system: str = "hospital_a"
    # patient_id -> {"gender": ..., "birthDate": ...}; used to refine observation mapping
    patients: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)

    @property
    def system_cfg(self):
        return self.config["systems"].get(self.source_system, {})

    def with_system(self, name):
        """Return a context for another source system, sharing patients/warnings."""
        return MappingContext(self.config, name or self.source_system, self.patients, self.warnings)

    def warn(self, message):
        self.warnings.append(f"[{self.source_system}] {message}")
