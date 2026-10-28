import unittest

from tools.fetch_skills import validate_manifest


class SkillManifestTests(unittest.TestCase):
    def test_required_skill_needs_source_and_license(self):
        manifest = {"skills": {"hyperframes": {"required": True}}}
        problems = validate_manifest(manifest)
        self.assertTrue(any("source" in item for item in problems))
        self.assertTrue(any("license" in item for item in problems))

    def test_agent_managed_skill_can_be_checked_without_clone_url(self):
        manifest = {"skills": {"imagegen": {
            "required": False,
            "source": {"type": "agent-managed", "name": "imagegen"},
            "license": "CHECK_BEFORE_USE",
        }}}
        self.assertEqual(validate_manifest(manifest), [])

    def test_git_source_must_pin_a_full_commit(self):
        manifest = {"skills": {"hyperframes": {
            "required": True,
            "source": {"type": "git", "repo": "https://example.invalid/repo", "commit": "main"},
            "license": "Apache-2.0",
        }}}
        self.assertTrue(any("40-character commit" in item for item in validate_manifest(manifest)))


if __name__ == "__main__":
    unittest.main()
