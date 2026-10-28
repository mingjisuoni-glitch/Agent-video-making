#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
demo_root="$(cd -- "$script_dir/.." && pwd)"
mkdir -p "$demo_root/build"

avm-captions \
  --transcript "$demo_root/transcript.json" \
  --json-output "$demo_root/build/captions.json" \
  --srt-output "$demo_root/build/captions.srt"
