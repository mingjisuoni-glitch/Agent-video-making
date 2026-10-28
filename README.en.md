# Agent Video Making

A reusable, content-neutral method kit for agent-assisted video production. It contains planning rules, a JSON-Schema-backed evidence gate, audio/caption-to-HyperFrames assembly, delivery manifests, a rendered-in-CI 12-second smoke example, and optional adapters for Volcano Engine TTS or a user-installed Qwen3-TTS model.

It does **not** contain a subject-specific script, production media, API credentials, voice-model weights, or permission to use third-party voices and assets.

Start with [docs/install.md](docs/install.md), then run:

```bash
python -m venv .venv
python -m pip install -e .
avm-doctor
```

The main artifact path is `avm-captions` → `avm-assemble` → `hyperframes check --strict --json` → `avm-preflight --with-checks` → render → `avm-manifest`. See [the getting-started guide](docs/getting-started.md) for exact commands and [video.schema.json](video.schema.json) for the plan structure source of truth.

External Skills are not all bundled. See [Skill sources, installation channels, and limitations](docs/skill-sources.md) for verified upstream repositories, pinned files, licenses, platform-only capabilities, and non-equivalent fallbacks.

The general method documents are Apache-2.0. The repository-provided voice workflow, code, and examples are noncommercial; see [LICENSE.md](LICENSE.md) for the file-level map and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for separate third-party terms.

