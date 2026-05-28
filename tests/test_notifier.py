import unittest

from src.notifier import format_message


class NotifierMessageTests(unittest.TestCase):
    def test_professor_group_includes_scraped_professor_name(self):
        message = format_message(
            title="Long-term Recruitment: LLMs, AI Agents and AI Systems",
            url="https://www.ssccuhksz.club/post/post-1",
            snippet="Researcher: Pin Gao | School: SDS | Status: OPEN | LLM, AI Agents",
            score=8,
            matched_keywords=["llm", "ai agents"],
            professor_group="Pin Gao Research Group",
            topic_area="AI systems",
        )

        self.assertIn("Professor/group: Pin Gao / Pin Gao Research Group", message)

    def test_professor_group_uses_scraped_professor_when_classifier_has_none(self):
        message = format_message(
            title="AutoResearch",
            url="https://www.ssccuhksz.club/post/post-2",
            snippet="Researcher: Prof. Chen | School: SDS | Status: OPEN",
            score=6,
            matched_keywords=["ai agent"],
        )

        self.assertIn("Professor/group: Prof. Chen", message)

    def test_summary_is_plain_text_not_markdown(self):
        message = format_message(
            title="AI-based embedding alignment",
            url="https://www.ssccuhksz.club/post/post-3",
            snippet=(
                "### Project Description\n"
                "- **Image** and `omics` embedding alignment\n"
                "1. Run [analysis](https://example.edu/analysis)\n"
                "Researcher: Prof. Wang | School: MED"
            ),
            score=7,
            matched_keywords=["ai"],
        )

        self.assertIn(
            "Summary: Project Description Image and omics embedding alignment "
            "Run analysis (https://example.edu/analysis) Researcher: Prof. Wang",
            message,
        )
        summary = message.split("Summary: ", 1)[1]
        self.assertNotIn("###", summary)
        self.assertNotIn("**", summary)
        self.assertNotIn("`", summary)
        self.assertNotIn("- ", summary)


if __name__ == "__main__":
    unittest.main()
