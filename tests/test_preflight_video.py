import unittest

from tools.preflight_video import validate_plan


def valid_plan():
    return {
        "ratio": "9:16",
        "resolution": "1080x1920",
        "duration_seconds": 12,
        "fps": 30,
        "style": {"id": "minimal-product", "confirmed": True},
        "voice": {"mode": "none", "confirmed": True},
        "approval": {"plan_approved": True},
        "creative_checks": {
            "no_static_card_sequence": True,
            "action_per_narrative_unit": True,
            "motivated_transitions": True,
            "captions_synced_to_final_audio": True,
            "license_reviewed": True,
            "layered_assets_ready": True,
            "three_state_shots": True,
            "final_audio_locked": True,
        },
    }


class PreflightTests(unittest.TestCase):
    def test_valid_plan_passes(self):
        self.assertEqual(validate_plan(valid_plan()), [])

    def test_missing_approval_and_failed_check_block_render(self):
        plan = valid_plan()
        plan["approval"]["plan_approved"] = False
        plan["creative_checks"]["motivated_transitions"] = False
        problems = validate_plan(plan)
        self.assertTrue(any("plan_approved" in item for item in problems))
        self.assertTrue(any("motivated_transitions" in item for item in problems))

    def test_tts_mode_requires_a_voice_id(self):
        plan = valid_plan()
        plan["voice"] = {"mode": "qwen3-local", "confirmed": True}
        self.assertTrue(any("voice_id" in item for item in validate_plan(plan)))

    def test_invalid_types_and_ranges_are_rejected(self):
        plan = valid_plan()
        plan.update({"resolution": "nope", "duration_seconds": "soon", "fps": -30})
        problems = validate_plan(plan)
        self.assertTrue(any("resolution" in item for item in problems))
        self.assertTrue(any("duration_seconds" in item for item in problems))
        self.assertTrue(any("fps" in item for item in problems))

    def test_ratio_must_match_resolution(self):
        plan = valid_plan()
        plan["resolution"] = "1920x1080"
        self.assertTrue(any("does not match" in item for item in validate_plan(plan)))


if __name__ == "__main__":
    unittest.main()

