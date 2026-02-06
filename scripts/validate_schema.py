#!/usr/bin/env python3
"""Basic schema validation for config.yml.

Checks that required top-level keys and nested project fields exist.
This avoids needing external jsonschema dependency.
"""
import sys
import yaml

REQUIRED_TOP_LEVEL = {
    "project": {"name": str, "seed": int},
    "sectioning": dict,
    "vui": dict,
    "spi": dict,
    "nli": dict,
    "ci": dict,
    "weights": dict,
    "bands": dict,
}

def validate(cfg):
    for key, spec in REQUIRED_TOP_LEVEL.items():
        if key not in cfg:
            raise KeyError(f"Missing required top-level key: {key}")
        if isinstance(spec, dict):
            sub = cfg[key]
            if not isinstance(sub, dict):
                raise TypeError(f"{key} must be a mapping")
            for sub_key, sub_type in spec.items():
                if sub_key not in sub:
                    raise KeyError(f"Missing {key}.{sub_key}")
                if not isinstance(sub[sub_key], sub_type):
                    raise TypeError(f"{key}.{sub_key} must be {sub_type.__name__}")
        else:
            if not isinstance(cfg[key], spec):
                raise TypeError(f"{key} must be {spec.__name__}")


def main(path: str = "config.yml") -> None:
    with open(path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    validate(cfg)
    print("schema ok")

if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "config.yml"
    main(target)
