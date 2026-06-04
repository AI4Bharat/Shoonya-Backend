import json
from unittest.mock import MagicMock, patch

from django.test import TestCase

from functions.utils import (
    OCR_MICROSERVICE_URL,
    get_batch_ocr_predictions,
    get_batch_ocr_predictions_using_arena,
)

# ─── Shared fixtures ──────────────────────────────────────────────────────────

MOCK_BBOXES = [
    {
        "x": 12.5,
        "y": 8.3,
        "width": 74.2,
        "height": 3.1,
        "text": "Sample paragraph text",
        "labels": ["Body"],
        "rotation": 0,
        "original_width": 1240,
        "original_height": 1754,
    }
]

MOCK_MICROSERVICE_RESPONSE = {
    "text": "Sample paragraph text",
    "bboxes": MOCK_BBOXES,
    "confidence": 0.97,
    "processing_time_ms": 843,
}


def make_mock_response(json_data, status_code=200):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_data
    mock_resp.raise_for_status = MagicMock()
    return mock_resp


# ─── get_batch_ocr_predictions_using_arena ────────────────────────────────────


class TestGetBatchOcrPredictionsUsingArena(TestCase):

    @patch("functions.utils.http_requests.post")
    def test_success_returns_json_string(self, mock_post):
        mock_post.return_value = make_mock_response(MOCK_MICROSERVICE_RESPONSE)

        result = get_batch_ocr_predictions_using_arena(
            id=1,
            image_url="https://example.com/image.png",
            language="hi",
        )

        self.assertIsInstance(result, str)
        parsed = json.loads(result)
        self.assertEqual(len(parsed), 1)
        self.assertEqual(parsed[0]["text"], "Sample paragraph text")
        self.assertAlmostEqual(parsed[0]["x"], 12.5)

    @patch("functions.utils.http_requests.post")
    def test_correct_payload_sent(self, mock_post):
        mock_post.return_value = make_mock_response(MOCK_MICROSERVICE_RESPONSE)

        get_batch_ocr_predictions_using_arena(
            id=1,
            image_url="https://example.com/image.png",
            language="ta",
        )

        mock_post.assert_called_once_with(
            f"{OCR_MICROSERVICE_URL}/ocr",
            json={"image_url": "https://example.com/image.png", "language": "ta"},
            timeout=120,
        )

    @patch("functions.utils.http_requests.post")
    def test_provider_override_included_in_payload(self, mock_post):
        mock_post.return_value = make_mock_response(MOCK_MICROSERVICE_RESPONSE)

        get_batch_ocr_predictions_using_arena(
            id=1,
            image_url="https://example.com/image.png",
            language="hi",
            provider="openai",
        )

        call_kwargs = mock_post.call_args
        sent_payload = call_kwargs[1]["json"]
        self.assertEqual(sent_payload["provider"], "openai")

    @patch("functions.utils.http_requests.post")
    def test_no_provider_field_when_not_specified(self, mock_post):
        mock_post.return_value = make_mock_response(MOCK_MICROSERVICE_RESPONSE)

        get_batch_ocr_predictions_using_arena(
            id=1,
            image_url="https://example.com/image.png",
        )

        call_kwargs = mock_post.call_args
        sent_payload = call_kwargs[1]["json"]
        self.assertNotIn("provider", sent_payload)

    @patch("functions.utils.http_requests.post")
    def test_connection_error_returns_empty_string(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.ConnectionError("refused")

        result = get_batch_ocr_predictions_using_arena(
            id=42,
            image_url="https://example.com/image.png",
        )

        self.assertEqual(result, "")

    @patch("functions.utils.http_requests.post")
    def test_timeout_returns_empty_string(self, mock_post):
        import requests as req
        mock_post.side_effect = req.exceptions.Timeout("timed out")

        result = get_batch_ocr_predictions_using_arena(
            id=42,
            image_url="https://example.com/image.png",
        )

        self.assertEqual(result, "")

    @patch("functions.utils.http_requests.post")
    def test_http_error_returns_empty_string(self, mock_post):
        import requests as req
        mock_resp = MagicMock()
        mock_resp.raise_for_status.side_effect = req.exceptions.HTTPError("503")
        mock_post.return_value = mock_resp

        result = get_batch_ocr_predictions_using_arena(
            id=42,
            image_url="https://example.com/image.png",
        )

        self.assertEqual(result, "")

    @patch("functions.utils.http_requests.post")
    def test_unexpected_exception_returns_empty_string(self, mock_post):
        mock_post.side_effect = RuntimeError("something exploded")

        result = get_batch_ocr_predictions_using_arena(
            id=42,
            image_url="https://example.com/image.png",
        )

        self.assertEqual(result, "")


# ─── get_batch_ocr_predictions dispatch ──────────────────────────────────────


class TestGetBatchOcrPredictionsDispatch(TestCase):

    @patch("functions.utils.get_batch_ocr_predictions_using_arena")
    def test_arena_api_type_calls_arena_function(self, mock_arena):
        mock_arena.return_value = json.dumps(MOCK_BBOXES)

        result = get_batch_ocr_predictions(
            id=1,
            image_url="https://example.com/image.png",
            api_type="arena",
        )

        mock_arena.assert_called_once_with(1, "https://example.com/image.png")
        self.assertEqual(result["status"], "Success")

    @patch("functions.utils.get_batch_ocr_predictions_using_arena")
    def test_arena_failure_returns_failure_status(self, mock_arena):
        mock_arena.return_value = ""

        result = get_batch_ocr_predictions(
            id=1,
            image_url="https://example.com/image.png",
            api_type="arena",
        )

        self.assertEqual(result["status"], "Failure")
        self.assertEqual(result["output"], "")

    def test_invalid_api_type_raises_value_error(self):
        with self.assertRaises(ValueError):
            get_batch_ocr_predictions(
                id=1,
                image_url="https://example.com/image.png",
                api_type="invalid-provider",
            )

    @patch("functions.utils.get_batch_ocr_predictions_using_google")
    def test_google_api_type_still_works(self, mock_google):
        mock_google.return_value = json.dumps(MOCK_BBOXES)

        result = get_batch_ocr_predictions(
            id=1,
            image_url="https://example.com/image.png",
            api_type="google",
        )

        mock_google.assert_called_once()
        self.assertEqual(result["status"], "Success")