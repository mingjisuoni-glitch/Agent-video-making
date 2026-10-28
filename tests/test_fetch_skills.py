import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tools.fetch_skills import inspect_manifest, validate_manifest


class SkillManifestTests(unittest.TestCase):
    def test_required_skill_needs_source_and_license(self):
        manifest = {"skills": {"hyperframes": {"required": True}}}
        problems = validate_manifest(manifest)
        self.assertTrue(any("source" in item for item in problems))
        self.assertTrue(any("license" in item for item in problems))
        self.assertTrue(any("availability" in item for item in problems))
        self.assertTrue(any("install_hint" in item for item in problems))

    def test_platform_skill_can_be_checked_without_clone_url(self):
        manifest = {"skills": {"imagegen": {
            "required": False,
            "availability": "platform-builtin",
            "source": {
                "type": "platform",
                "platform": "OpenAI Codex",
                "documentation_url": "https://example.invalid/imagegen",
            },
            "license": "NOASSERTION",
            "install_hint": "Use the capability bundled with Codex.",
        }}}
        self.assertEqual(validate_manifest(manifest), [])

    def test_git_source_must_pin_a_full_commit(self):
        manifest = {"skills": {"hyperframes": {
            "required": True,
            "source": {"type": "git", "repo": "https://example.invalid/repo", "commit": "main"},
            "license": "Apache-2.0",
            "availability": "public-git",
            "install_hint": "example",
        }}}
        self.assertTrue(any("40-character commit" in item for item in validate_manifest(manifest)))

    def test_git_source_must_pin_skill_file_hash(self):
        manifest = {"skills": {"hyperframes": {
            "required": True,
            "source": {
                "type": "git", "repo": "https://example.invalid/repo", "commit": "a" * 40,
            },
            "license": "Apache-2.0",
            "availability": "public-git",
            "install_hint": "example",
        }}}
        self.assertTrue(any("skill_sha256" in item for item in validate_manifest(manifest)))

    def test_git_source_must_declare_skill_path(self):
        manifest = {"skills": {"example": {
            "required": False,
            "availability": "public-git",
            "source": {
                "type": "git",
                "repo": "https://example.invalid/repo",
                "commit": "a" * 40,
                "skill_sha256": "b" * 64,
            },
            "license": "MIT",
            "install_hint": "example",
        }}}
        self.assertTrue(any("skill_path" in item for item in validate_manifest(manifest)))

    def test_local_only_skill_requires_an_alternative_or_explanation(self):
        manifest = {"skills": {"private-skill": {
            "required": False,
            "availability": "local-only",
            "source": {"type": "local-only", "name": "private-skill"},
            "license": "NOASSERTION",
            "install_hint": "No public installer.",
        }}}
        self.assertTrue(any("alternative" in item for item in validate_manifest(manifest)))

    def test_installed_git_skill_hash_is_verified(self):
        with tempfile.TemporaryDirectory() as folder:
            skill = Path(folder) / "hyperframes"
            skill.mkdir()
            (skill / "SKILL.md").write_bytes(b"known skill")
            manifest = {"skills": {"hyperframes": {
                "required": True,
                "source": {
                    "type": "git",
                    "repo": "https://example.invalid/repo",
                    "commit": "a" * 40,
                    "skill_path": "skills/hyperframes/SKILL.md",
                    "skill_sha256": hashlib.sha256(b"different").hexdigest(),
                },
                "license": "Apache-2.0",
                "availability": "public-git",
                "install_hint": "example",
            }}}
            result = inspect_manifest(manifest, [Path(folder)])[0]
            self.assertEqual(result["state"], "fail")

    def test_alternate_installed_path_is_detected(self):
        with tempfile.TemporaryDirectory() as folder:
            skill = Path(folder) / "motion-design-agent" / "skills" / "remotion"
            skill.mkdir(parents=True)
            (skill / "SKILL.md").write_bytes(b"nested skill")
            manifest = {"skills": {"remotion": {
                "required": False,
                "availability": "public-git",
                "installed_paths": ["motion-design-agent/skills/remotion"],
                "source": {
                    "type": "git",
                    "repo": "https://example.invalid/repo",
                    "commit": "a" * 40,
                    "skill_path": "skills/remotion/SKILL.md",
                    "skill_sha256": hashlib.sha256(b"nested skill").hexdigest(),
                },
                "license": "MIT",
                "install_hint": "example",
            }}}
            result = inspect_manifest(manifest, [Path(folder)])[0]
            self.assertEqual(result["state"], "ok")
            self.assertTrue(result["installed_path"].endswith("motion-design-agent\\skills\\remotion") or
                            result["installed_path"].endswith("motion-design-agent/skills/remotion"))

    def test_committed_manifest_is_complete(self):
        manifest_path = Path(__file__).parents[1] / "skills" / "manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.assertEqual(validate_manifest(manifest), [])


if __name__ == "__main__":
    unittest.main()
