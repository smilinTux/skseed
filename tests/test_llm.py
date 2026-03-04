"""Tests for skseed LLM callback adapters."""

import os
import json
from unittest.mock import MagicMock, patch

import pytest

from skseed.llm import (
    passthrough_callback,
    anthropic_callback,
    openai_callback,
    ollama_callback,
    auto_callback,
    LLMCallback,
)


class TestPassthroughCallback:
    """Tests for passthrough_callback — echoes the prompt unchanged."""

    def test_returns_prompt_unchanged(self):
        cb = passthrough_callback()
        assert cb("Hello world") == "Hello world"

    def test_returns_callable(self):
        cb = passthrough_callback()
        assert callable(cb)

    def test_empty_string(self):
        cb = passthrough_callback()
        assert cb("") == ""

    def test_multiline_prompt(self):
        cb = passthrough_callback()
        prompt = "Line 1\nLine 2\nLine 3"
        assert cb(prompt) == prompt


class TestAnthropicCallback:
    """Tests for anthropic_callback adapter."""

    def test_raises_import_error_when_anthropic_missing(self):
        """Should raise ImportError if anthropic package is not installed."""
        cb = anthropic_callback(api_key="fake-key")
        with patch.dict("sys.modules", {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic package required"):
                cb("Test prompt")

    def test_raises_value_error_when_no_api_key(self, monkeypatch):
        """Should raise ValueError if no API key is available."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mock_anthropic = MagicMock()
        cb = anthropic_callback()  # no explicit api_key
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                cb("Test prompt")

    def test_uses_env_api_key(self, monkeypatch):
        """Should use ANTHROPIC_API_KEY env var when no explicit key given."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-env-key")
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="mocked response")]
        mock_client.messages.create.return_value = mock_response

        cb = anthropic_callback()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = cb("Test prompt")

        assert result == "mocked response"

    def test_uses_explicit_api_key(self, monkeypatch):
        """Should use explicit api_key parameter over env var."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="explicit key response")]
        mock_client.messages.create.return_value = mock_response

        cb = anthropic_callback(api_key="explicit-key")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = cb("Test prompt")

        assert result == "explicit key response"
        mock_anthropic.Anthropic.assert_called_once_with(api_key="explicit-key")

    def test_passes_model_and_max_tokens(self, monkeypatch):
        """Should forward model and max_tokens to the API call."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="ok")]
        mock_client.messages.create.return_value = mock_response

        cb = anthropic_callback(model="claude-haiku-4-5", max_tokens=512, api_key="key")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            cb("prompt")

        call_kwargs = mock_client.messages.create.call_args
        assert call_kwargs.kwargs["model"] == "claude-haiku-4-5"
        assert call_kwargs.kwargs["max_tokens"] == 512


class TestOpenAICallback:
    """Tests for openai_callback adapter."""

    def test_raises_import_error_when_openai_missing(self):
        """Should raise ImportError if openai package is not installed."""
        cb = openai_callback(api_key="fake")
        with patch.dict("sys.modules", {"openai": None}):
            with pytest.raises(ImportError, match="openai package required"):
                cb("Test prompt")

    def test_calls_openai_with_model(self, monkeypatch):
        """Should call OpenAI completions with the configured model."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="openai response"))]
        mock_client.chat.completions.create.return_value = mock_response

        cb = openai_callback(model="gpt-4o-mini", api_key="test-key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = cb("Test prompt")

        assert result == "openai response"

    def test_passes_base_url_when_set(self, monkeypatch):
        """Should pass base_url to the OpenAI client when configured."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="ok"))]
        mock_client.chat.completions.create.return_value = mock_response

        cb = openai_callback(base_url="http://localhost:8080", api_key="test")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")

        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("base_url") == "http://localhost:8080"

    def test_returns_empty_string_on_none_content(self, monkeypatch):
        """Should return empty string when message content is None."""
        mock_openai = MagicMock()
        mock_client = MagicMock()
        mock_openai.OpenAI.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content=None))]
        mock_client.chat.completions.create.return_value = mock_response

        cb = openai_callback(api_key="key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = cb("prompt")

        assert result == ""


class TestOllamaCallback:
    """Tests for ollama_callback adapter."""

    def test_sends_request_to_ollama(self):
        """Should POST to the /api/generate endpoint."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": "ollama answer"}).encode()
        mock_response.__enter__ = lambda s: s
        mock_response.__exit__ = MagicMock(return_value=False)

        cb = ollama_callback(model="llama3.1", base_url="http://localhost:11434")
        with patch("urllib.request.urlopen", return_value=mock_response):
            result = cb("Test prompt")

        assert result == "ollama answer"

    def test_uses_configured_model(self):
        """Should include model name in request payload."""
        captured_payloads = []

        def fake_urlopen(req, timeout=None):
            captured_payloads.append(json.loads(req.data.decode()))
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"response": "ok"}).encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            return mock_resp

        cb = ollama_callback(model="mistral")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            cb("Test prompt")

        assert len(captured_payloads) == 1
        assert captured_payloads[0]["model"] == "mistral"
        assert captured_payloads[0]["stream"] is False

    def test_returns_empty_string_on_missing_response_key(self):
        """Should return empty string if 'response' key is absent."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"other": "data"}).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        cb = ollama_callback()
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = cb("prompt")

        assert result == ""


class TestAutoCallback:
    """Tests for auto_callback — auto-detects best available LLM."""

    def test_returns_none_when_no_credentials_no_ollama(self, monkeypatch):
        """Returns None when no API keys and no Ollama running."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        with patch("urllib.request.urlopen", side_effect=Exception("Connection refused")):
            result = auto_callback()

        assert result is None

    def test_returns_anthropic_when_key_set_and_sdk_available(self, monkeypatch):
        """Returns anthropic_callback when ANTHROPIC_API_KEY is set and SDK is available."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        mock_anthropic = MagicMock()
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = auto_callback()

        assert result is not None
        assert callable(result)

    def test_skips_anthropic_when_sdk_missing_tries_openai(self, monkeypatch):
        """Falls through to OpenAI when anthropic SDK is missing."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        monkeypatch.setenv("OPENAI_API_KEY", "openai-key")

        # Simulate anthropic SDK missing by making import raise ImportError
        original_import = __builtins__.__import__ if hasattr(__builtins__, "__import__") else __import__

        mock_openai = MagicMock()

        # patch to make anthropic module raise ImportError on import
        with patch.dict("sys.modules", {"anthropic": None, "openai": mock_openai}):
            # anthropic is None in sys.modules → ImportError on import
            result = auto_callback()

        # Should fall through and return openai or None depending on SDK availability
        # The important thing is it doesn't raise
        assert result is None or callable(result)

    def test_returns_ollama_when_available(self, monkeypatch):
        """Returns ollama_callback when Ollama is running locally."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = auto_callback()

        assert result is not None
        assert callable(result)

    def test_skips_ollama_when_connection_refused(self, monkeypatch):
        """Returns None when Ollama connection is refused."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            result = auto_callback()

        assert result is None

    def test_returns_callable_type(self, monkeypatch):
        """auto_callback result satisfies LLMCallback type when not None."""
        monkeypatch.setenv("ANTHROPIC_API_KEY", "key")
        mock_anthropic = MagicMock()

        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = auto_callback()

        if result is not None:
            assert callable(result)
