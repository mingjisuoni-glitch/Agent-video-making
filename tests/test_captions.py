import unittest

from voice.captions import format_srt, group_words


class CaptionTests(unittest.TestCase):
    def test_groups_only_at_natural_pauses(self):
        words = [
            {"text": "先", "start": 0.0, "end": 0.2},
            {"text": "确认", "start": 0.22, "end": 0.6},
            {"text": "方案", "start": 0.92, "end": 1.3},
        ]
        groups = group_words(words, pause_gap=0.28, max_chars=18)
        self.assertEqual([item["text"] for item in groups], ["先确认", "方案"])
        self.assertEqual(groups[0]["end"], 0.6)

    def test_long_unpaused_phrase_is_flagged_not_arbitrarily_split(self):
        words = [
            {"text": char, "start": index * 0.1, "end": index * 0.1 + 0.08}
            for index, char in enumerate("这是一个没有自然停顿的超长字幕测试")
        ]
        groups = group_words(words, pause_gap=0.28, max_chars=8)
        self.assertEqual(len(groups), 1)
        self.assertTrue(groups[0]["over_limit"])

    def test_srt_uses_group_boundaries(self):
        srt = format_srt([{"text": "测试", "start": 1.0, "end": 2.25}])
        self.assertIn("00:00:01,000 --> 00:00:02,250", srt)
        self.assertTrue(srt.endswith("\n"))


if __name__ == "__main__":
    unittest.main()

