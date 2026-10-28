#!/usr/bin/env bash
set -euo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
demo_root="$(cd -- "$script_dir/.." && pwd)"
build_dir="$demo_root/build"
mkdir -p "$build_dir/segments"

for command_name in espeak-ng ffmpeg ffprobe; do
  command -v "$command_name" >/dev/null 2>&1 || {
    echo "missing required command: $command_name" >&2
    exit 1
  }
done

phrases=(
  "真实音频"
  "生成字幕"
  "按停顿分组"
  "切换三个场景"
  "运行严格检查"
  "交付证据齐全"
)

for index in "${!phrases[@]}"; do
  number=$((index + 1))
  raw="$build_dir/segments/raw-${number}.wav"
  segment="$build_dir/segments/segment-${number}.wav"
  espeak-ng -v zh -s 150 -w "$raw" "${phrases[$index]}"
  ffmpeg -hide_banner -loglevel error -y -i "$raw" \
    -af "apad,atrim=duration=2" -ar 24000 -ac 1 -c:a pcm_s16le "$segment"
done

ffmpeg -hide_banner -loglevel error -y -f lavfi -i "anullsrc=r=24000:cl=mono" \
  -t 0.5 -c:a pcm_s16le "$build_dir/segments/lead.wav"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "anullsrc=r=24000:cl=mono" \
  -t 1 -c:a pcm_s16le "$build_dir/segments/gap.wav"
ffmpeg -hide_banner -loglevel error -y -f lavfi -i "anullsrc=r=24000:cl=mono" \
  -t 2.5 -c:a pcm_s16le "$build_dir/segments/tail.wav"

concat_file="$build_dir/segments/concat.txt"
{
  printf "file '%s'\n" "$build_dir/segments/lead.wav"
  for number in 1 2 3 4 5 6; do
    printf "file '%s'\n" "$build_dir/segments/segment-${number}.wav"
    if [[ "$number" -lt 6 ]]; then
      printf "file '%s'\n" "$build_dir/segments/gap.wav"
    fi
  done
  printf "file '%s'\n" "$build_dir/segments/tail.wav"
} > "$concat_file"

ffmpeg -hide_banner -loglevel error -y -f concat -safe 0 -i "$concat_file" \
  -t 20 -ar 24000 -ac 1 -c:a pcm_s16le "$build_dir/final.wav"

duration="$(ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 "$build_dir/final.wav")"
python - "$duration" <<'PY'
import sys

duration = float(sys.argv[1])
assert abs(duration - 20.0) < 0.01, duration
PY
