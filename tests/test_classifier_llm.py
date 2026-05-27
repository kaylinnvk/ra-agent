import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from src import classifier

RESULTS_FILE_ENV = "LLM_CLASSIFIER_RESULTS_FILE"
RUN_LIVE_LLM_ENV = "RUN_LIVE_LLM_TESTS"
RUN_ALL_LIVE_LLM_ENV = "RUN_ALL_LIVE_LLM_TESTS"


def llm_settings():
    return SimpleNamespace(
        use_llm_classifier=True,
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_base_url=os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip(),
    )


def live_llm_tests_enabled():
    return os.getenv(RUN_LIVE_LLM_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def all_live_llm_tests_enabled():
    return os.getenv(RUN_ALL_LIVE_LLM_ENV, "").strip().lower() in {"1", "true", "yes", "on"}


def skip_unless_live_llm_configured():
    settings = llm_settings()
    if not live_llm_tests_enabled():
        raise unittest.SkipTest(f"Set {RUN_LIVE_LLM_ENV}=true to run live LLM API tests.")
    if not settings.gemini_api_key:
        raise unittest.SkipTest("GEMINI_API_KEY is required for live LLM API tests.")
    return settings


def skip_unless_all_live_llm_tests_enabled():
    if not all_live_llm_tests_enabled():
        raise unittest.SkipTest(f"Set {RUN_ALL_LIVE_LLM_ENV}=true to run all live LLM API tests.")


def classify_with_live_llm(title, snippet, min_score, settings):
    keyword_result = classifier.classify_with_keywords(
        title=title,
        snippet=snippet,
        min_score=min_score,
    )
    with patch.object(classifier, "settings", settings):
        return classifier.classify_with_llm(
            title=title,
            snippet=snippet,
            min_score=min_score,
            keyword_result=keyword_result,
        )


def error_details(exc):
    details = {
        "type": type(exc).__name__,
        "message": str(exc),
    }
    response = getattr(exc, "response", None)
    if response is not None:
        details["status_code"] = response.status_code
        details["response_headers"] = dict(response.headers)
        details["response_body"] = response.text
    return details


def write_llm_result(test_name, title, snippet, result):
    results_file = os.getenv(RESULTS_FILE_ENV)
    if not results_file:
        return

    path = Path(results_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    classification_result = asdict(result)
    classification_result.pop("raw_llm_response", None)

    payload = {
        "test": test_name,
        "input": {
            "title": title,
            "snippet": snippet,
        },
        "llm_response": result.raw_llm_response,
        "classification_result": classification_result,
    }

    with path.open("a", encoding="utf-8") as file:
        file.write(f"## {test_name}\n\n")
        file.write("### Input\n\n")
        file.write(f"Title: {title}\n\n")
        file.write(f"Snippet: {snippet}\n\n")
        file.write("### LLM Response\n\n")
        file.write("```json\n")
        file.write(json.dumps(payload["llm_response"], ensure_ascii=False, indent=2))
        file.write("\n```\n\n")
        file.write("### Parsed Classification Result\n\n")
        file.write("```json\n")
        file.write(json.dumps(payload["classification_result"], ensure_ascii=False, indent=2))
        file.write("\n```\n\n")


def report_name(test_case):
    names = {
        "test_classifies_realistic_ai_ra_opening_as_relevant": "Relevant AI/LLM RA Opening",
        "test_rejects_research_news_that_is_not_an_opening": "AI Seminar Is Not An RA Opening",
        "test_uses_keyword_matches_when_llm_returns_no_keywords": "Student Helper Vision Opening",
        "test_falls_back_to_keyword_classifier_when_llm_request_fails": "Keyword Fallback When LLM Fails",
    }
    return names.get(test_case._testMethodName, test_case.id())


def write_llm_error(test_name, title, snippet, exc):
    results_file = os.getenv(RESULTS_FILE_ENV)
    if not results_file:
        return

    path = Path(results_file)
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("a", encoding="utf-8") as file:
        file.write(f"## {test_name}\n\n")
        file.write("### Input\n\n")
        file.write(f"Title: {title}\n\n")
        file.write(f"Snippet: {snippet}\n\n")
        file.write("### API Error\n\n")
        file.write("```json\n")
        file.write(json.dumps(error_details(exc), ensure_ascii=False, indent=2))
        file.write("\n```\n\n")


def classify_and_write_report(test_case, title, snippet, min_score, settings):
    try:
        result = classify_with_live_llm(
            title=title,
            snippet=snippet,
            min_score=min_score,
            settings=settings,
        )
    except Exception as exc:
        write_llm_error(report_name(test_case), title, snippet, exc)
        raise

    write_llm_result(report_name(test_case), title, snippet, result)
    return result


class LLMClassifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        results_file = os.getenv(RESULTS_FILE_ENV)
        if results_file:
            Path(results_file).write_text("# LLM Classifier Test Results\n\n", encoding="utf-8")

    def test_classifies_realistic_ai_ra_opening_as_relevant(self):
        test_settings = skip_unless_live_llm_configured()
        title = "Research Assistant - LLM Agents for Scientific Discovery"
        snippet = (
            "Build agentic AI systems for literature review and experiment planning. | "
            "Requirements: Python, machine learning, natural language processing, "
            "and strong writing skills. | Prof. Maya Chen | School of Computing | "
            "Open | Deadline: 2026-06-30 | Tags: RA, LLM, AI agents"
        )

        result = classify_and_write_report(
            self,
            title,
            snippet,
            6,
            test_settings,
        )

        self.assertTrue(result.is_ra_opening)
        self.assertTrue(result.is_relevant)
        self.assertEqual(result.source, "llm")
        self.assertGreaterEqual(result.score, 6)
        self.assertTrue(result.raw_llm_response)
        self.assertIn("llm", " ".join(result.matched_keywords).lower())

    def test_rejects_research_news_that_is_not_an_opening(self):
        skip_unless_all_live_llm_tests_enabled()
        test_settings = skip_unless_live_llm_configured()
        title = "AI Research Seminar: Multimodal Foundation Models"
        snippet = (
            "Talk announcement for a weekly seminar. | Speaker: Dr. Arun Patel | "
            "School of Computing | Date: 2026-06-12 | Tags: seminar, machine learning"
        )

        result = classify_and_write_report(
            self,
            title,
            snippet,
            2,
            test_settings,
        )

        self.assertFalse(result.is_ra_opening)
        self.assertFalse(result.is_relevant)
        self.assertEqual(result.source, "llm")
        self.assertTrue(result.raw_llm_response)

    def test_uses_keyword_matches_when_llm_returns_no_keywords(self):
        skip_unless_all_live_llm_tests_enabled()
        test_settings = skip_unless_live_llm_configured()
        title = "Student Helper Opening - Computer Vision Safety Lab"
        snippet = (
            "Assist with dataset curation for computer vision and deepfake detection. | "
            "Requirements: ML experience preferred. | Prof. Lina Gomez | "
            "Open | Deadline: Rolling | Tags: student helper, CV, deepfake"
        )

        result = classify_and_write_report(
            self,
            title,
            snippet,
            5,
            test_settings,
        )

        self.assertTrue(result.is_relevant)
        self.assertEqual(result.source, "llm")
        self.assertTrue(result.is_ra_opening)
        self.assertGreaterEqual(result.score, 5)
        self.assertTrue(result.raw_llm_response)

    def test_falls_back_to_keyword_classifier_when_llm_request_fails(self):
        title = "Research Intern Opening - Reinforcement Learning for AI Systems"
        snippet = (
            "Join a research group building reinforcement learning methods for AI systems. | "
            "Requirements: Python and ML. | Prof. Jordan Lee | Status: Open | "
            "Deadline: 2026-07-15 | Tags: research internship, RL"
        )

        with (
            patch.object(classifier, "settings", llm_settings()),
            patch.object(classifier.requests, "post", side_effect=RuntimeError("network down")),
            patch("builtins.print"),
        ):
            result = classifier.classify_text(title=title, snippet=snippet, min_score=2)

        self.assertEqual(result.source, "keyword")
        self.assertTrue(result.is_ra_opening)
        self.assertTrue(result.is_relevant)
        self.assertIn("research intern", result.matched_keywords)
        self.assertIn("reinforcement learning", result.matched_keywords)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--llm-results-file",
        help=(
            "Write LLM responses and parsed classifier results to this file. "
            f"Equivalent to setting {RESULTS_FILE_ENV}."
        ),
    )
    parser.add_argument(
        "--live-llm",
        action="store_true",
        help=f"Run one smoke test against the real configured LLM API. Equivalent to setting {RUN_LIVE_LLM_ENV}=true.",
    )
    parser.add_argument(
        "--live-llm-all",
        action="store_true",
        help=(
            "Run all live LLM API tests. This can consume more quota. "
            f"Equivalent to setting {RUN_LIVE_LLM_ENV}=true and {RUN_ALL_LIVE_LLM_ENV}=true."
        ),
    )
    known_args, unittest_args = parser.parse_known_args()

    if known_args.llm_results_file:
        os.environ[RESULTS_FILE_ENV] = known_args.llm_results_file
    if known_args.live_llm or known_args.live_llm_all:
        os.environ[RUN_LIVE_LLM_ENV] = "true"
    if known_args.live_llm_all:
        os.environ[RUN_ALL_LIVE_LLM_ENV] = "true"

    unittest.main(argv=[sys.argv[0], *unittest_args])
