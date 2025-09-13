import json, glob
from pathlib import Path
from jsonschema import Draft7Validator

SCHEMA_PATH = Path('schema/run.schema.json')

def main():
    schema = json.loads(SCHEMA_PATH.read_text())
    validator = Draft7Validator(schema)
    files = sorted(glob.glob('outputs/run_*.json') + glob.glob('outputs/*/run_*.json'))
    if not files:
        print('No run files found.')
        return
    ok = True
    for path in files:
        data = json.loads(Path(path).read_text())
        errors = sorted(validator.iter_errors(data), key=lambda e: e.path)
        if errors:
            ok = False
            print(f'{path} failed validation:')
            for err in errors:
                loc = '.'.join(str(p) for p in err.path)
                print(f'  {loc}: {err.message}')
        else:
            print(f'{path}: OK')
    if not ok:
        raise SystemExit(1)

if __name__ == '__main__':
    main()
