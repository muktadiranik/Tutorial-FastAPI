"""Exercise the Streamlit workflow without making requests to Groq."""

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from langchain_core.messages import AIMessage
from streamlit.testing.v1 import AppTest

APP_FILE = Path(__file__).with_name("app.py")
REPORT = "Hemoglobin: 13 g/dL | Reference: 12-16 g/dL"
ANALYSIS = "- Hemoglobin: 13 g/dL | Status: NORMAL | Reference: 12-16 g/dL"
DIET = "Summary: The reported test is within range.\n\n## Foods to avoid\nExcess sugar.\n\n## Foods to eat more of\nDal."


class BloodWorkAppTests(unittest.TestCase):
    """Verify input handling, the two model calls, and persistent results."""

    def setUp(self) -> None:
        """Isolate credentials and replace the provider before running the app."""
        self.addCleanup(patch.stopall)
        patch.dict(os.environ, {"GROQ_API_KEY": "test-key"}).start()
        self.dotenv_values = patch("dotenv.dotenv_values", return_value={}).start()
        self.provider = patch("langchain_groq.ChatGroq").start()
        self.provider.return_value.invoke.side_effect = [AIMessage(content=ANALYSIS), AIMessage(content=DIET)]
        self.app = AppTest.from_file(str(APP_FILE), default_timeout=30).run()

    def fill_report(self) -> None:
        """Provide a report; credentials are supplied by the test environment."""
        self.app.text_area(key="report_text").input(REPORT)

    def analyze(self) -> None:
        """Select the main action and execute the resulting rerun."""
        next(button for button in self.app.button if button.label == "Analyze report").click().run()

    def test_initial_page_and_empty_report(self) -> None:
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.title[0].value, "Blood Work & Diet")
        self.assertEqual([field.label for field in self.app.text_input], ["Groq model"])
        self.analyze()
        self.assertIn("Add a blood report", self.app.error[0].value)
        self.provider.assert_not_called()

    def test_missing_key(self) -> None:
        self.app.text_area(key="report_text").input(REPORT)
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.analyze()
        self.assertIn("Set GROQ_API_KEY", self.app.error[0].value)
        self.provider.assert_not_called()

    def test_local_dotenv_key(self) -> None:
        self.fill_report()
        self.dotenv_values.return_value = {"GROQ_API_KEY": "dotenv-key"}
        with patch.dict(os.environ, {"GROQ_API_KEY": ""}):
            self.analyze()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.error)
        self.assertEqual(self.provider.call_args.kwargs["api_key"], "dotenv-key")

    def test_missing_model(self) -> None:
        self.fill_report()
        self.app.sidebar.text_input[0].input("  ")
        self.analyze()
        self.assertIn("Enter a Groq model", self.app.error[0].value)
        self.provider.assert_not_called()

    def test_analysis_persists_without_extra_requests(self) -> None:
        self.fill_report()
        self.analyze()
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.error)
        self.assertEqual(self.provider.call_args.kwargs["api_key"], "test-key")
        self.assertEqual(self.app.session_state["result"]["diet"], DIET)
        calls = self.provider.return_value.invoke.call_args_list
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0].args[0][1], ("human", REPORT))
        self.assertEqual(calls[1].args[0][1], ("human", ANALYSIS))
        self.app.run()
        self.assertEqual(self.provider.return_value.invoke.call_count, 2)
        self.assertEqual(len(self.app.get("download_button")), 1)
        self.app.text_area(key="report_text").input("Changed report").run()
        self.assertTrue(any("previous input" in item.value for item in self.app.info))
        self.app.sidebar.button[0].click().run()
        self.assertNotIn("result", self.app.session_state)

    def test_partial_result_survives_provider_failure(self) -> None:
        self.provider.return_value.invoke.side_effect = [AIMessage(content=ANALYSIS), RuntimeError("private details")]
        self.fill_report()
        self.analyze()
        self.assertFalse(self.app.exception)
        self.assertEqual(self.app.session_state["result"]["analysis"], ANALYSIS)
        self.assertEqual(self.app.session_state["result"]["diet"], "")
        self.assertIn("could not be completed", self.app.error[0].value)
        self.assertNotIn("private details", self.app.error[0].value)

    def test_notebook_report_resolves_from_app_directory(self) -> None:
        original_read_text = Path.read_text

        def read_text(path: Path, *args, **kwargs) -> str:
            if path == APP_FILE.with_name("blood_work.txt"):
                return REPORT
            return original_read_text(path, *args, **kwargs)

        with patch.object(Path, "read_text", autospec=True, side_effect=read_text) as reader:
            self.app.radio[0].set_value("Use notebook report").run()
            reader.assert_any_call(APP_FILE.with_name("blood_work.txt"), encoding="utf-8-sig")
        self.assertFalse(self.app.exception)
        self.assertFalse(self.app.error)
        self.assertEqual(self.app.text_area[0].value, REPORT)
        self.provider.assert_not_called()


if __name__ == "__main__":
    unittest.main()
