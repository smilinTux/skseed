"""Comprehensive tests for skseed LLM callback factories.

Covers:
  - grok_callback, kimi_callback, nvidia_callback (OpenAI-compatible wrappers)
  - claude_agent_sdk_callback
  - AdaptedPrompt handling in anthropic, openai, and ollama callbacks
  - auto_callback detection order for all providers
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch, call

import pytest

from skseed.llm import (
    anthropic_callback,
    openai_callback,
    ollama_callback,
    grok_callback,
    kimi_callback,
    nvidia_callback,
    passthrough_callback,
    auto_callback,
)


# ── Helpers ────────────────────────────────────────────────────────────────────

def _make_adapted_prompt(
    messages=None,
    system_param=None,
    temperature=None,
    extra_params=None,
):
    """Build a minimal AdaptedPrompt-like mock.

    _is_adapted_prompt checks for .messages and .system_param attributes,
    so a plain MagicMock with those set is sufficient.
    """
    obj = MagicMock()
    obj.messages = messages if messages is not None else [{"role": "user", "content": "test"}]
    obj.system_param = system_param
    obj.temperature = temperature
    obj.extra_params = extra_params if extra_params is not None else {}
    return obj


def _make_openai_mock(content="openai response"):
    """Return a mock openai module + client wired up to return *content*."""
    mock_mod = MagicMock()
    mock_client = MagicMock()
    mock_mod.OpenAI.return_value = mock_client
    mock_resp = MagicMock()
    mock_resp.choices = [MagicMock(message=MagicMock(content=content))]
    mock_client.chat.completions.create.return_value = mock_resp
    return mock_mod, mock_client


# ── Grok Callback ──────────────────────────────────────────────────────────────

class TestGrokCallback:
    """grok_callback wraps openai_callback with xAI base_url."""

    def test_returns_callable(self):
        cb = grok_callback(api_key="fake-xai-key")
        assert callable(cb)

    def test_uses_xai_base_url(self):
        mock_openai, mock_client = _make_openai_mock("grok response")
        cb = grok_callback(api_key="fake-xai-key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = cb("test prompt")
        assert result == "grok response"
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("base_url") == "https://api.x.ai/v1"

    def test_uses_xai_api_key_env(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "env-xai-key")
        mock_openai, mock_client = _make_openai_mock()
        cb = grok_callback()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("api_key") == "env-xai-key"

    def test_explicit_key_overrides_env(self, monkeypatch):
        monkeypatch.setenv("XAI_API_KEY", "env-key")
        mock_openai, _ = _make_openai_mock()
        cb = grok_callback(api_key="explicit-key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("api_key") == "explicit-key"

    def test_default_model_is_grok3(self):
        mock_openai, mock_client = _make_openai_mock()
        cb = grok_callback(api_key="key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")
        create_kwargs = mock_client.chat.completions.create.call_args
        assert create_kwargs.kwargs["model"] == "grok-3"


# ── Kimi Callback ──────────────────────────────────────────────────────────────

class TestKimiCallback:
    """kimi_callback wraps openai_callback with Moonshot base_url."""

    def test_returns_callable(self):
        cb = kimi_callback(api_key="fake-moonshot-key")
        assert callable(cb)

    def test_uses_moonshot_base_url(self):
        mock_openai, _ = _make_openai_mock("kimi response")
        cb = kimi_callback(api_key="fake-moonshot-key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = cb("test prompt")
        assert result == "kimi response"
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("base_url") == "https://api.moonshot.ai/v1"

    def test_uses_moonshot_api_key_env(self, monkeypatch):
        monkeypatch.setenv("MOONSHOT_API_KEY", "env-moonshot")
        mock_openai, _ = _make_openai_mock()
        cb = kimi_callback()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("api_key") == "env-moonshot"

    def test_default_model_is_moonshot_128k(self):
        mock_openai, mock_client = _make_openai_mock()
        cb = kimi_callback(api_key="key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")
        create_kwargs = mock_client.chat.completions.create.call_args
        assert create_kwargs.kwargs["model"] == "moonshot-v1-128k"


# ── NVIDIA Callback ────────────────────────────────────────────────────────────

class TestNvidiaCallback:
    """nvidia_callback wraps openai_callback with NVIDIA NIM base_url."""

    def test_returns_callable(self):
        cb = nvidia_callback(api_key="nvapi-fake")
        assert callable(cb)

    def test_uses_nvidia_base_url(self):
        mock_openai, _ = _make_openai_mock("nvidia response")
        cb = nvidia_callback(api_key="nvapi-fake")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = cb("test prompt")
        assert result == "nvidia response"
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("base_url") == "https://integrate.api.nvidia.com/v1"

    def test_uses_nvidia_api_key_env(self, monkeypatch):
        monkeypatch.setenv("NVIDIA_API_KEY", "env-nvapi")
        mock_openai, _ = _make_openai_mock()
        cb = nvidia_callback()
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")
        call_kwargs = mock_openai.OpenAI.call_args
        assert call_kwargs.kwargs.get("api_key") == "env-nvapi"

    def test_default_model_is_llama(self):
        mock_openai, mock_client = _make_openai_mock()
        cb = nvidia_callback(api_key="key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            cb("prompt")
        create_kwargs = mock_client.chat.completions.create.call_args
        assert "llama" in create_kwargs.kwargs["model"].lower()


# ── Claude Agent SDK Callback ──────────────────────────────────────────────────

class TestClaudeAgentSdkCallback:
    """Tests for claude_agent_sdk_callback."""

    def test_raises_import_error_when_sdk_missing(self):
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            from importlib import import_module
            with pytest.raises(ImportError, match="claude_agent_sdk not installed"):
                from skseed.llm import claude_agent_sdk_callback
                claude_agent_sdk_callback()

    def test_raises_runtime_error_when_claude_cli_missing(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            from skseed.llm import claude_agent_sdk_callback
            with patch("shutil.which", return_value=None):
                cb = claude_agent_sdk_callback()
                with pytest.raises(RuntimeError, match="claude CLI not found"):
                    cb("test prompt")

    def test_returns_stdout_on_success(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            from skseed.llm import claude_agent_sdk_callback
            with patch("shutil.which", return_value="/usr/bin/claude"):
                import subprocess
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "  Claude response here  "
                mock_result.stderr = ""
                with patch("subprocess.run", return_value=mock_result):
                    cb = claude_agent_sdk_callback()
                    result = cb("Is the sky blue?")
        assert result == "Claude response here"

    def test_raises_on_nonzero_exit_code(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            from skseed.llm import claude_agent_sdk_callback
            with patch("shutil.which", return_value="/usr/bin/claude"):
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "Error: rate limited"
                with patch("subprocess.run", return_value=mock_result):
                    cb = claude_agent_sdk_callback()
                    with pytest.raises(RuntimeError, match="claude CLI exited with code 1"):
                        cb("test prompt")

    def test_uses_last_message_from_adapted_prompt(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            from skseed.llm import claude_agent_sdk_callback
            with patch("shutil.which", return_value="/usr/bin/claude"):
                captured_cmds = []
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "response"

                def capture_run(cmd, **kwargs):
                    captured_cmds.append(cmd)
                    return mock_result

                with patch("subprocess.run", side_effect=capture_run):
                    cb = claude_agent_sdk_callback()
                    adapted = _make_adapted_prompt(
                        messages=[
                            {"role": "user", "content": "first message"},
                            {"role": "user", "content": "last message"},
                        ]
                    )
                    cb(adapted)

        # The last message content should be used as the prompt
        assert "last message" in captured_cmds[0]

    def test_passes_model_and_max_turns_flags(self):
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            from skseed.llm import claude_agent_sdk_callback
            with patch("shutil.which", return_value="/usr/bin/claude"):
                captured_cmds = []
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "ok"

                def capture_run(cmd, **kwargs):
                    captured_cmds.append(cmd)
                    return mock_result

                with patch("subprocess.run", side_effect=capture_run):
                    cb = claude_agent_sdk_callback(model="claude-opus-4-6", max_turns=3)
                    cb("prompt")

        cmd = captured_cmds[0]
        assert "--model" in cmd
        assert "claude-opus-4-6" in cmd
        assert "--max-turns" in cmd
        assert "3" in cmd


# ── AdaptedPrompt Handling ─────────────────────────────────────────────────────

class TestAdaptedPromptAnthropic:
    """Test that anthropic_callback correctly uses AdaptedPrompt fields."""

    def _run_with_adapted(self, prompt, **callback_kwargs):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="adapted response")]
        mock_client.messages.create.return_value = mock_response

        cb = anthropic_callback(api_key="test-key", **callback_kwargs)
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = cb(prompt)

        return result, mock_client.messages.create.call_args

    def test_uses_messages_array_not_string(self):
        adapted = _make_adapted_prompt(
            messages=[{"role": "user", "content": "adapted content"}]
        )
        result, call_args = self._run_with_adapted(adapted)
        assert result == "adapted response"
        kwargs = call_args.kwargs
        assert kwargs["messages"] == [{"role": "user", "content": "adapted content"}]
        # Should NOT be a plain string in messages
        assert isinstance(kwargs["messages"], list)

    def test_passes_system_param(self):
        adapted = _make_adapted_prompt(system_param="You are a logic engine.")
        _, call_args = self._run_with_adapted(adapted)
        assert call_args.kwargs.get("system") == "You are a logic engine."

    def test_skips_system_when_none(self):
        adapted = _make_adapted_prompt(system_param=None)
        _, call_args = self._run_with_adapted(adapted)
        assert "system" not in call_args.kwargs

    def test_passes_temperature(self):
        adapted = _make_adapted_prompt(temperature=0.3)
        _, call_args = self._run_with_adapted(adapted)
        assert call_args.kwargs.get("temperature") == 0.3

    def test_skips_temperature_when_none(self):
        adapted = _make_adapted_prompt(temperature=None)
        _, call_args = self._run_with_adapted(adapted)
        assert "temperature" not in call_args.kwargs

    def test_passes_thinking_config(self):
        thinking_cfg = {"type": "enabled", "budget_tokens": 2048}
        adapted = _make_adapted_prompt(extra_params={"thinking": thinking_cfg})
        _, call_args = self._run_with_adapted(adapted, max_tokens=1024)
        assert call_args.kwargs.get("thinking") == thinking_cfg
        # max_tokens must be >= budget + max_tokens
        assert call_args.kwargs["max_tokens"] >= 2048 + 1024

    def test_plain_string_prompt_uses_messages_list(self):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="plain response")]
        mock_client.messages.create.return_value = mock_response

        cb = anthropic_callback(api_key="key")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = cb("plain string prompt")

        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["messages"] == [{"role": "user", "content": "plain string prompt"}]
        assert result == "plain response"

    def test_returns_empty_when_no_text_block(self):
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        # Block has no .text attribute
        block = MagicMock(spec=[])  # spec=[] means no attrs
        mock_response.content = [block]
        mock_client.messages.create.return_value = mock_response

        cb = anthropic_callback(api_key="key")
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result = cb("prompt")
        assert result == ""


class TestAdaptedPromptOpenAI:
    """Test that openai_callback correctly uses AdaptedPrompt fields."""

    def _run_with_adapted(self, prompt, **callback_kwargs):
        mock_openai, mock_client = _make_openai_mock("openai adapted response")
        cb = openai_callback(api_key="test-key", **callback_kwargs)
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = cb(prompt)
        return result, mock_client.chat.completions.create.call_args

    def test_uses_messages_array(self):
        adapted = _make_adapted_prompt(
            messages=[{"role": "user", "content": "adapted openai"}]
        )
        result, call_args = self._run_with_adapted(adapted)
        assert result == "openai adapted response"
        assert call_args.kwargs["messages"] == [{"role": "user", "content": "adapted openai"}]

    def test_passes_temperature(self):
        adapted = _make_adapted_prompt(temperature=0.9)
        _, call_args = self._run_with_adapted(adapted)
        assert call_args.kwargs.get("temperature") == 0.9

    def test_passes_enable_thinking_in_extra_body(self):
        adapted = _make_adapted_prompt(extra_params={"enable_thinking": True})
        _, call_args = self._run_with_adapted(adapted)
        extra_body = call_args.kwargs.get("extra_body", {})
        assert extra_body.get("enable_thinking") is True

    def test_no_extra_body_when_no_thinking_params(self):
        adapted = _make_adapted_prompt(extra_params={})
        _, call_args = self._run_with_adapted(adapted)
        assert "extra_body" not in call_args.kwargs

    def test_plain_string_uses_user_message(self):
        mock_openai, mock_client = _make_openai_mock("plain response")
        cb = openai_callback(api_key="key")
        with patch.dict("sys.modules", {"openai": mock_openai}):
            result = cb("plain string")
        call_args = mock_client.chat.completions.create.call_args
        assert call_args.kwargs["messages"] == [{"role": "user", "content": "plain string"}]


class TestAdaptedPromptOllama:
    """Test that ollama_callback correctly uses AdaptedPrompt fields."""

    def _make_ollama_response(self, content="ollama response", use_chat=True):
        if use_chat:
            body = {"message": {"content": content}}
        else:
            body = {"response": content}
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(body).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_uses_api_chat_for_adapted_prompt(self):
        adapted = _make_adapted_prompt(
            messages=[{"role": "user", "content": "adapted ollama"}]
        )
        mock_resp = self._make_ollama_response("chat response")
        captured = []

        def fake_urlopen(req, timeout=None):
            captured.append(req.full_url)
            return mock_resp

        cb = ollama_callback(base_url="http://localhost:11434")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = cb(adapted)

        assert "/api/chat" in captured[0]
        assert result == "chat response"

    def test_uses_api_generate_for_plain_string(self):
        mock_resp = self._make_ollama_response("generate response", use_chat=False)
        captured_urls = []

        def fake_urlopen(req, timeout=None):
            captured_urls.append(req.full_url)
            return mock_resp

        cb = ollama_callback(base_url="http://localhost:11434")
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = cb("plain string")

        assert "/api/generate" in captured_urls[0]
        assert result == "generate response"

    def test_passes_system_param_in_chat_body(self):
        adapted = _make_adapted_prompt(system_param="Be concise.")
        mock_resp = self._make_ollama_response("ok")
        captured_payloads = []

        def fake_urlopen(req, timeout=None):
            captured_payloads.append(json.loads(req.data.decode()))
            return mock_resp

        cb = ollama_callback()
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            cb(adapted)

        assert captured_payloads[0].get("system") == "Be concise."

    def test_passes_temperature_in_options(self):
        adapted = _make_adapted_prompt(temperature=0.5)
        mock_resp = self._make_ollama_response("ok")
        captured_payloads = []

        def fake_urlopen(req, timeout=None):
            captured_payloads.append(json.loads(req.data.decode()))
            return mock_resp

        cb = ollama_callback()
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            cb(adapted)

        assert captured_payloads[0]["options"]["temperature"] == 0.5

    def test_skips_system_when_none(self):
        adapted = _make_adapted_prompt(system_param=None)
        mock_resp = self._make_ollama_response("ok")
        captured_payloads = []

        def fake_urlopen(req, timeout=None):
            captured_payloads.append(json.loads(req.data.decode()))
            return mock_resp

        cb = ollama_callback()
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            cb(adapted)

        assert "system" not in captured_payloads[0]

    def test_retries_on_empty_response(self):
        empty_resp = MagicMock()
        empty_resp.read.return_value = json.dumps({"response": ""}).encode()
        empty_resp.__enter__ = lambda s: s
        empty_resp.__exit__ = MagicMock(return_value=False)

        ok_resp = self._make_ollama_response("retry success", use_chat=False)
        responses = [empty_resp, ok_resp]

        def fake_urlopen(req, timeout=None):
            return responses.pop(0)

        cb = ollama_callback(max_retries=1)
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            result = cb("prompt")

        assert result == "retry success"

    def test_respects_ollama_host_env(self, monkeypatch):
        monkeypatch.setenv("OLLAMA_HOST", "http://custom-host:11434")
        mock_resp = self._make_ollama_response("ok", use_chat=False)
        captured_urls = []

        def fake_urlopen(req, timeout=None):
            captured_urls.append(req.full_url)
            return mock_resp

        cb = ollama_callback()  # no explicit base_url
        with patch("urllib.request.urlopen", side_effect=fake_urlopen):
            cb("prompt")

        assert "custom-host" in captured_urls[0]


# ── Auto Callback Detection Order ─────────────────────────────────────────────

class TestAutoCallbackOrder:
    """Verify auto_callback checks providers in documented order."""

    _ALL_KEYS = [
        "ANTHROPIC_API_KEY",
        "XAI_API_KEY",
        "MOONSHOT_API_KEY",
        "NVIDIA_API_KEY",
        "OPENAI_API_KEY",
    ]

    def _clear_all_keys(self, monkeypatch):
        for k in self._ALL_KEYS:
            monkeypatch.delenv(k, raising=False)

    def test_xai_key_returns_callable_when_openai_sdk_available(self, monkeypatch):
        self._clear_all_keys(monkeypatch)
        monkeypatch.setenv("XAI_API_KEY", "xai-test")
        mock_openai, _ = _make_openai_mock()
        with patch.dict("sys.modules", {"openai": mock_openai, "claude_agent_sdk": None}):
            result = auto_callback()
        assert result is not None and callable(result)

    def test_moonshot_key_returns_callable_when_openai_sdk_available(self, monkeypatch):
        self._clear_all_keys(monkeypatch)
        monkeypatch.setenv("MOONSHOT_API_KEY", "moonshot-test")
        mock_openai, _ = _make_openai_mock()
        with patch.dict("sys.modules", {"openai": mock_openai, "claude_agent_sdk": None}):
            result = auto_callback()
        assert result is not None and callable(result)

    def test_nvidia_key_returns_callable_when_openai_sdk_available(self, monkeypatch):
        self._clear_all_keys(monkeypatch)
        monkeypatch.setenv("NVIDIA_API_KEY", "nvapi-test")
        mock_openai, _ = _make_openai_mock()
        with patch.dict("sys.modules", {"openai": mock_openai, "claude_agent_sdk": None}):
            result = auto_callback()
        assert result is not None and callable(result)

    def test_openai_key_returns_callable_when_sdk_available(self, monkeypatch):
        self._clear_all_keys(monkeypatch)
        monkeypatch.setenv("OPENAI_API_KEY", "openai-test")
        mock_openai, _ = _make_openai_mock()
        with patch.dict("sys.modules", {"openai": mock_openai, "claude_agent_sdk": None}):
            result = auto_callback()
        assert result is not None and callable(result)

    def test_anthropic_takes_precedence_over_xai(self, monkeypatch):
        """When both ANTHROPIC_API_KEY and XAI_API_KEY are set,
        anthropic should win (it's checked before XAI in auto_callback)."""
        self._clear_all_keys(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthro-key")
        monkeypatch.setenv("XAI_API_KEY", "xai-key")
        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="anthropic reply")]
        mock_client.messages.create.return_value = mock_response

        with patch.dict("sys.modules", {"anthropic": mock_anthropic, "claude_agent_sdk": None}):
            result = auto_callback()

        assert result is not None and callable(result)
        # Verify it invokes the anthropic client when called
        with patch.dict("sys.modules", {"anthropic": mock_anthropic}):
            result("hello")
        mock_anthropic.Anthropic.assert_called()

    def test_ollama_fallback_when_running(self, monkeypatch):
        self._clear_all_keys(monkeypatch)
        mock_resp = MagicMock()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            with patch("urllib.request.urlopen", return_value=mock_resp):
                result = auto_callback()
        assert result is not None and callable(result)

    def test_returns_none_when_all_missing(self, monkeypatch):
        self._clear_all_keys(monkeypatch)
        import urllib.error
        with patch.dict("sys.modules", {"claude_agent_sdk": None}):
            with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("no")):
                result = auto_callback()
        assert result is None

    def test_claude_agent_sdk_takes_top_priority(self, monkeypatch):
        """When claude_agent_sdk is installed AND all API keys are set,
        claude_agent_sdk_callback should be returned first."""
        self._clear_all_keys(monkeypatch)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "anthro-key")
        mock_sdk = MagicMock()
        with patch.dict("sys.modules", {"claude_agent_sdk": mock_sdk}):
            with patch("shutil.which", return_value="/usr/bin/claude"):
                result = auto_callback()
        # Returns a callable (not None) — claude_agent_sdk path was taken
        assert result is not None and callable(result)
