# Artifact Pipeline and Evidence Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the audio→captions→HyperFrames gap, replace self-declared gates with artifact evidence, generate a reproducible delivery manifest, and make `video.schema.json` the structural source of truth.

**Architecture:** Add two focused CLIs: `avm-assemble` builds a self-contained HyperFrames project from audio, pause-grouped captions, and scene declarations; `avm-manifest` probes final artifacts and writes their hashes, provenance, check report, environment, and Skill pins. `avm-preflight` delegates structural validation to JSON Schema, then performs only cross-field and evidence semantics. Shared probing/hashing code lives in one small artifact utility module.

**Tech Stack:** Python 3.10+, `jsonschema` Draft 2020-12, FFmpeg/ffprobe, HyperFrames 0.8.210, GSAP 3.14.2, Node.js 22, `unittest`, GitHub Actions.

**Spec:** `D:\ds项目\项目一\Agent-video-making-主要问题.md`

## Global Constraints

- `avm-assemble scenes.json --out <dir>` must derive duration from the actual audio through ffprobe and compute `total_frames = round(duration_seconds * fps)`.
- Scene boundaries must be caption-group boundaries; no time-based equal splitting.
- Generated HyperFrames files must use deterministic paused GSAP timelines, matching composition/timeline ids, templated sub-compositions, graphics/captions tracks, and motion sidecars with `keepsMoving` plus `staysInFrame`.
- `avm-preflight --with-checks <report>` only accepts `ok=true`, `strict=true`, and `browserSkipped=false`.
- Evidence paths are resolved relative to the plan file, must exist, and must be parseable; caption group counts and caption/audio duration must agree.
- `video.schema.json` owns all field types, required fields, positive ranges, and conditional `voice_id`; Python owns only ratio/resolution reduction, frame arithmetic, evidence semantics, and cross-artifact checks.
- Missing inputs to `avm-manifest` are fatal; it embeds the complete HyperFrames report and hashes every delivered artifact.
- The voiced demo audio is generated locally and remains untracked; CI checks the generated project but does not render it.
- The hello-video CI job renders a smoke MP4 and rejects a duration error of 0.05 seconds or more.

## Review Focus

- Captions with fewer groups than scenes: assembler must fail with a useful error rather than invent non-boundary cuts (Task 2 test).
- Captions ending slightly after the audio: preflight must reject totals above 103% while allowing normal timestamp rounding (Task 1 test).
- TTS plans whose audio evidence is unreadable or missing: preflight must fail before HyperFrames checks are considered (Task 1 test).
- Delivery run with stale or mismatched sidecars: manifest must report the artifact hashes it actually reads and reject absent provenance (Task 4 test).
- ffprobe output with multiple streams or fractional frame rates: probing must select the video stream, normalize `avg_frame_rate`, and preserve codec/dimensions (Task 2 and Task 4 tests).

---

### Task 1: Schema-Driven Preflight With Artifact Evidence

**Files:**
- Modify: `video.schema.json`
- Modify: `tools/preflight_video.py`
- Modify: `examples/video-plan.example.json`
- Create: `examples/evidence/creative-review.json`
- Create: `examples/evidence/captions.json`
- Create: `examples/evidence/no-audio.json`
- Modify: `tests/test_preflight_video.py`
- Modify: `pyproject.toml`
- Modify: `requirements-dev.txt`

**Interfaces:**
- Produces: `load_and_validate_plan(plan_path: Path, schema_path: Path | None = None, checks_path: Path | None = None) -> tuple[dict, list[str]]`.
- Produces: `validate_plan(plan: dict, base_dir: Path, check_report: dict | None = None) -> list[str]` for semantic checks after JSON Schema succeeds.
- Produces: creative-check objects shaped as `{"ok": true, "evidence": "relative/path", ...}`; caption sync additionally requires integer `groups`.

- [x] **Step 1: Write failing schema/preflight tests** for `resolution="0x0"`, non-integer fps, missing conditional `voice_id`, incorrect `total_frames`, missing/unparseable evidence, caption group mismatch, caption duration >103% of audio, and failed/non-strict/browser-skipped HyperFrames reports.
- [x] **Step 2: Run `python -m unittest tests.test_preflight_video -v` and verify failures are caused by the old boolean-only gate.**
- [x] **Step 3: Update `video.schema.json`** with positive resolution, integer `fps`, required integer `total_frames`, conditional TTS `voice_id`, evidence-check definitions, and closed nested objects.
- [x] **Step 4: Replace duplicate type checks in `tools/preflight_video.py`** with Draft 2020-12 `jsonschema` validation; retain only ratio reduction, frame arithmetic, evidence parsing, caption/audio duration, and check-report semantics.
- [x] **Step 5: Convert the example plan and add parseable example evidence**; no-voice evidence must explicitly declare `{"mode":"none","locked":true}` and caption evidence must be an empty list with `groups=0` in the plan.
- [x] **Step 6: Run the focused tests and full suite; expect all passing.**

### Task 2: Shared Artifact Probes and `avm-assemble`

**Files:**
- Create: `tools/artifacts.py`
- Create: `voice/assemble.py`
- Create: `tests/test_artifacts.py`
- Create: `tests/test_assemble.py`
- Modify: `pyproject.toml`
- Modify: `LICENSE.md`

**Interfaces:**
- Produces: `sha256_file(path: Path, limit: int | None = None) -> str`.
- Produces: `probe_media(path: Path, runner=subprocess.run) -> dict` returning duration and normalized audio/video stream facts.
- Produces: `build_project(config_path: Path, output_dir: Path, probe=probe_media) -> dict` returning `duration_seconds`, `total_frames`, scene windows, and generated files.
- Consumes: caption JSON as a list of `{text,start,end,over_limit}`.

- [x] **Step 1: Write failing probe tests** for ffprobe JSON, fractional FPS, unreadable media, and SHA-256.
- [x] **Step 2: Run `python -m unittest tests.test_artifacts -v` and verify the module is missing.**
- [x] **Step 3: Implement `tools/artifacts.py`** with one ffprobe JSON call, normalized duration/FPS, deterministic stream selection, and hashing.
- [x] **Step 4: Write failing assembler tests** proving real audio duration drives root duration/frame count, scene cuts equal caption-group starts, too-few groups fail, captions occupy their own track, scenes occupy graphics tracks, sub-compositions are templated, timelines are paused/id-matched, banned clocks are absent, and every scene has the required motion assertions.
- [x] **Step 5: Run `python -m unittest tests.test_assemble -v` and verify failures are caused by the missing CLI.**
- [x] **Step 6: Implement `voice/assemble.py`** and register `avm-assemble`; resolve inputs relative to `scenes.json`, copy audio into `assets/`, partition ordered caption groups deterministically by group count, and write `index.html`, sub-compositions, sidecars, `package.json`, lock-independent metadata, `hyperframes.json`, and `meta.json`.
- [x] **Step 7: Run focused tests and the full suite; expect all passing.**

### Task 3: Reproducible Voiced Demo and Strict HyperFrames Check

**Files:**
- Create: `examples/voiced-demo/scenes.json`
- Create: `examples/voiced-demo/transcript.json`
- Create: `examples/voiced-demo/scripts/make-audio.sh`
- Create: `examples/voiced-demo/scripts/make-captions.sh`
- Create: `examples/voiced-demo/scripts/build.sh`
- Create: `examples/voiced-demo/README.md`
- Modify: `.gitignore`
- Modify: `.github/workflows/ci.yml`

**Interfaces:**
- Consumes: `avm-captions` and `avm-assemble` from Tasks 1–2.
- Produces: an ignored `examples/voiced-demo/generated/` project with exactly 20 seconds of generated narration audio and three caption-boundary scenes.

- [x] **Step 1: Add a failing integration assertion** to CI/local script that expects `generated/index.html` and a strict HyperFrames report with zero errors/warnings.
- [x] **Step 2: Run `bash examples/voiced-demo/scripts/build.sh` and verify it fails because the demo inputs/scripts are incomplete.**
- [x] **Step 3: Add deterministic narration generation** using `espeak-ng` plus ffmpeg padding/trimming to exactly 20 seconds; generate captions from the committed word transcript, then assemble the project.
- [x] **Step 4: Install generated project dependencies and run `npm run check`; fix generator output until `check --strict` reports zero errors and zero warnings.**
- [x] **Step 5: Add the voiced-demo check to CI** with `espeak-ng` installation and without rendering this demo.

### Task 4: Provenance Sidecars and `avm-manifest`

**Files:**
- Create: `tools/delivery_manifest.py`
- Create: `tests/test_delivery_manifest.py`
- Modify: `voice/cli.py`
- Modify: `voice/captions.py`
- Modify: `tools/doctor.py`
- Modify: `tests/test_cli_features.py`
- Modify: `tests/test_captions.py`
- Modify: `tests/test_doctor.py`
- Modify: `pyproject.toml`
- Modify: `LICENSE.md`

**Interfaces:**
- Produces: audio `<file>.avm.json` with provider, speaker, audio hash, duration, and model `model_sha256`/`head_sha256` aggregates captured at synthesis time.
- Produces: caption `<captions>.avm.json` with group count, over-limit count, source kind, and canonical transcript SHA-256.
- Produces: `environment_snapshot(root: Path) -> dict` in `tools.doctor`.
- Produces: `build_delivery_manifest(plan, video, audio, captions, checks, skills, root) -> dict` and CLI `avm-manifest`.

- [x] **Step 1: Write failing sidecar tests** for single/batch TTS provenance and caption transcript provenance.
- [x] **Step 2: Run focused tests and verify failure because sidecars lack the required provenance.**
- [x] **Step 3: Extend synthesis and caption commands** to write provenance sidecars atomically after successful outputs; refactor model provenance to expose aggregate full/head hashes without changing provider behavior.
- [x] **Step 4: Write failing manifest tests** for video probe fields/hash, audio provenance, caption counts/hash, complete check embedding, environment versions, Skill pins, missing inputs, and tampered artifact hash behavior.
- [x] **Step 5: Run `python -m unittest tests.test_delivery_manifest -v` and verify failure because `avm-manifest` is missing.**
- [x] **Step 6: Implement `tools/delivery_manifest.py`** and register `avm-manifest`; discover the newest check report unless `--checks` is supplied, but reject discovery ambiguity and any missing required input.
- [x] **Step 7: Run focused tests and full suite; expect all passing.**

### Task 5: Render Smoke, Documentation, and End-to-End Verification

**Files:**
- Modify: `.github/workflows/ci.yml`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `docs/install.md`
- Modify: `docs/getting-started.md`
- Modify: `AGENTS.md`
- Modify: `CHANGELOG.md`
- Modify: `LICENSE.md`

**Interfaces:**
- Consumes: all previous CLIs and example artifacts.
- Produces: documented end-to-end commands and CI evidence for both strict checks and a real 12-second encode.

- [x] **Step 1: Add the hello-video render smoke step**: `npm run render`, assert non-empty MP4, read duration with ffprobe, and fail unless `abs(duration - 12.0) < 0.05`.
- [x] **Step 2: Update documentation** with `video.schema.json`, evidence objects, `avm-assemble`, voiced-demo setup, `--with-checks`, and `avm-manifest` examples.
- [x] **Step 3: Run `python -m unittest discover -s tests -q`, Ruff, manifest validation, JSON Schema example validation, and both example strict checks.**
- [x] **Step 4: Render only the 12-second hello-video smoke and verify ffprobe duration/fps/codec; do not render the voiced demo.**
- [x] **Step 5: Run `git diff --check`, review the complete diff against all four spec sections, and report any remaining limitation explicitly.**
