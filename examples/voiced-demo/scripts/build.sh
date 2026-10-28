#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
demo_root="$(cd -- "$script_dir/.." && pwd)"
generated_dir="$demo_root/generated"

if [[ "$generated_dir" != "$demo_root/generated" ]]; then
  echo "refusing to remove unexpected output path: $generated_dir" >&2
  exit 1
fi
rm -rf -- "$generated_dir"

bash "$script_dir/make-audio.sh"
bash "$script_dir/make-captions.sh"
avm-assemble "$demo_root/scenes.json" --out "$generated_dir"
test -s "$generated_dir/index.html"

(
  cd "$generated_dir"
  npm install
  npm run --silent check -- --json > check-raw.json
)

python - "$generated_dir/check-raw.json" "$generated_dir/check-report.json" <<'PY'
import json
import sys
from pathlib import Path

raw_path, report_path = map(Path, sys.argv[1:])
report = json.loads(raw_path.read_text(encoding="utf-8"))

def count(level):
    key = f"{level}Count"
    return sum(
        value.get(key, 0)
        for value in report.values()
        if isinstance(value, dict) and isinstance(value.get(key, 0), int)
    )

report["errors"] = count("errors")
report["warnings"] = count("warnings")
report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
assert report['strict'] is True
assert report['ok'] is True
assert report['browserSkipped'] is False
assert report['errors'] == 0
assert report['warnings'] == 0
PY

test -s "$generated_dir/index.html"
echo "voiced demo passed strict HyperFrames checks: $generated_dir"
