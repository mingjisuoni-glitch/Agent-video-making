# Agent Video Making

A reusable, content-neutral method kit for agent-assisted video production. It contains planning rules, a render preflight gate, a checked 12-second HyperFrames example, and optional adapters for Volcano Engine TTS or a user-installed Qwen3-TTS model.

It does **not** contain a subject-specific script, production media, API credentials, voice-model weights, or permission to use third-party voices and assets.

Start with [docs/install.md](docs/install.md), then run:

```bash
python -m venv .venv
python -m pip install -e .
avm-doctor
```

The general method documents are Apache-2.0. The repository-provided voice workflow, code, and examples are noncommercial; see [LICENSE.md](LICENSE.md) for the file-level map and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for separate third-party terms.

