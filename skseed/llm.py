"""
LLM callback providers for the skseed collider.

The collider is model-agnostic — it generates prompts and accepts any
callable that takes a prompt string and returns a response string.

This module provides ready-made callbacks for common setups:

  - claude_agent_sdk_callback: Uses the Claude Agent SDK (claude CLI subprocess)
  - anthropic_callback: Uses the Anthropic SDK (Claude)
  - openai_callback: Uses the OpenAI SDK (+ compatible APIs)
  - ollama_callback: Uses a local Ollama instance
  - grok_callback: Uses xAI Grok via OpenAI-compatible API
  - kimi_callback: Uses Moonshot Kimi via OpenAI-compatible API
  - nvidia_callback: Uses NVIDIA NIM via OpenAI-compatible API
  - passthrough_callback: Returns the prompt as-is (for debugging/testing)

All callbacks accept either a plain str prompt (legacy) or an
AdaptedPrompt object from the prompt adapter (new — uses per-model
temperature, system_param, thinking config, etc.).

Usage:
    from skseed import Collider
    from skseed.llm import anthropic_callback

    collider = Collider(llm=anthropic_callback())
    result = collider.collide("Truth is knowable")
"""

from __future__ import annotations

import os
from typing import Any, Callable, Optional, Union

LLMCallback = Callable[[str], str]


def _is_adapted_prompt(prompt: Any) -> bool:
    """Check if prompt is an AdaptedPrompt without hard-importing skcapstone."""
    return hasattr(prompt, "messages") and hasattr(prompt, "system_param")


def anthropic_callback(
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 4096,
    api_key: Optional[str] = None,
) -> LLMCallback:
    """Create a callback that uses the Anthropic (Claude) API.

    Accepts either a plain string prompt or an AdaptedPrompt object.
    When given an AdaptedPrompt, uses system_param, temperature, and
    thinking config for optimal Claude formatting.

    Args:
        model: Model ID to use.
        max_tokens: Maximum response tokens.
        api_key: API key. Falls back to ANTHROPIC_API_KEY env var.

    Returns:
        LLM callback function.
    """
    def _call(prompt: Union[str, Any]) -> str:
        try:
            import anthropic
        except ImportError:
            raise ImportError(
                "anthropic package required. Install with: pip install anthropic"
            )

        key = api_key or os.environ.get("ANTHROPIC_API_KEY", "")
        if not key:
            raise ValueError(
                "ANTHROPIC_API_KEY not set. Set it or pass api_key parameter."
            )

        client = anthropic.Anthropic(api_key=key)

        if _is_adapted_prompt(prompt):
            kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": prompt.messages,
            }
            if prompt.system_param:
                kwargs["system"] = prompt.system_param
            if prompt.temperature is not None:
                kwargs["temperature"] = prompt.temperature
            # Thinking config from extra_params
            if "thinking" in prompt.extra_params:
                kwargs["thinking"] = prompt.extra_params["thinking"]
                # Extended thinking requires higher max_tokens
                budget = prompt.extra_params["thinking"].get("budget_tokens", 4096)
                kwargs["max_tokens"] = max(max_tokens, budget + max_tokens)
            message = client.messages.create(**kwargs)
        else:
            message = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )

        # Extract text from response (skip thinking blocks)
        for block in message.content:
            if hasattr(block, "text"):
                return block.text
        return ""

    return _call


def openai_callback(
    model: str = "gpt-4o",
    max_tokens: int = 4096,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> LLMCallback:
    """Create a callback that uses the OpenAI API (or compatible).

    Also serves as the base for Grok, Kimi, and NVIDIA NIM callbacks
    via the base_url parameter.

    Accepts either a plain string prompt or an AdaptedPrompt object.

    Args:
        model: Model ID to use.
        max_tokens: Maximum response tokens.
        api_key: API key. Falls back to OPENAI_API_KEY env var.
        base_url: Optional base URL for compatible APIs.

    Returns:
        LLM callback function.
    """
    def _call(prompt: Union[str, Any]) -> str:
        try:
            import openai
        except ImportError:
            raise ImportError(
                "openai package required. Install with: pip install openai"
            )

        key = api_key or os.environ.get("OPENAI_API_KEY", "")
        client_kwargs: dict[str, Any] = {"api_key": key}
        if base_url:
            client_kwargs["base_url"] = base_url

        client = openai.OpenAI(**client_kwargs)

        if _is_adapted_prompt(prompt):
            create_kwargs: dict[str, Any] = {
                "model": model,
                "max_tokens": max_tokens,
                "messages": prompt.messages,
            }
            if prompt.temperature is not None:
                create_kwargs["temperature"] = prompt.temperature
            # Pass through extra params (enable_thinking, etc.) via extra_body
            # so the OpenAI SDK doesn't reject them as unknown kwargs.
            extra_body: dict[str, Any] = {}
            for key_name in ("enable_thinking",):
                if key_name in prompt.extra_params:
                    extra_body[key_name] = prompt.extra_params[key_name]
            if extra_body:
                create_kwargs["extra_body"] = extra_body
            response = client.chat.completions.create(**create_kwargs)
        else:
            response = client.chat.completions.create(
                model=model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
        return response.choices[0].message.content or ""

    return _call


def ollama_callback(
    model: str = "llama3.1",
    base_url: Optional[str] = None,
    max_retries: int = 1,
) -> LLMCallback:
    """Create a callback that uses a local Ollama instance.

    Accepts either a plain string prompt or an AdaptedPrompt object.
    When given an AdaptedPrompt (has .messages), uses /api/chat with the
    messages array and optional system field. Falls back to /api/generate
    for plain string prompts.

    Respects OLLAMA_HOST env var (same as the probe in LLMBridge).

    Args:
        model: Model name to use.
        base_url: Ollama server URL. Defaults to OLLAMA_HOST env var or
            http://localhost:11434.
        max_retries: Retries on empty or failed response (default 1).

    Returns:
        LLM callback function.
    """
    # Resolve base_url at callback-creation time so it's consistent
    # with _probe_ollama which also reads OLLAMA_HOST.
    resolved_url = base_url or os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    # Strip trailing slash to avoid double-slash in endpoint paths
    resolved_url = resolved_url.rstrip("/")

    def _call(prompt: Union[str, Any]) -> str:
        import json
        import urllib.request

        def _parse_response(raw: bytes) -> str:
            """Parse Ollama response body.

            Handles both single-JSON (stream=False) and NDJSON (streaming),
            since Ollama may emit chunked lines even when stream=False is set.
            Also guards against None content fields.
            """
            text = raw.decode("utf-8").strip()
            if not text:
                return ""
            # Happy path: single JSON object (stream=False)
            try:
                result = json.loads(text)
                if "message" in result:
                    return result["message"].get("content", "") or ""
                return result.get("response", "") or ""
            except json.JSONDecodeError:
                pass
            # Fallback: NDJSON — aggregate non-empty content chunks
            chunks: list[str] = []
            for line in text.splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    obj = json.loads(line)
                    if "message" in obj:
                        content = obj["message"].get("content", "") or ""
                    else:
                        content = obj.get("response", "") or ""
                    if content:
                        chunks.append(content)
                except json.JSONDecodeError:
                    continue
            return "".join(chunks)

        def _build_payload() -> tuple[bytes, str]:
            if _is_adapted_prompt(prompt):
                body: dict[str, Any] = {
                    "model": model,
                    "messages": prompt.messages,
                    "stream": False,
                }
                if getattr(prompt, "system_param", None):
                    body["system"] = prompt.system_param
                if prompt.temperature is not None:
                    body["options"] = {"temperature": prompt.temperature}
                return json.dumps(body).encode("utf-8"), f"{resolved_url}/api/chat"
            return json.dumps({
                "model": model,
                "prompt": str(prompt),
                "stream": False,
            }).encode("utf-8"), f"{resolved_url}/api/generate"

        last_exc: Optional[Exception] = None
        for attempt in range(max_retries + 1):
            try:
                payload, endpoint = _build_payload()
                req = urllib.request.Request(
                    endpoint,
                    data=payload,
                    headers={"Content-Type": "application/json"},
                )
                # Use a generous timeout: CPU-only inference can take 60-180s.
                # The LLMBridge._timed_call() enforces the tier-level deadline.
                with urllib.request.urlopen(req, timeout=300) as resp:
                    raw = resp.read()
                response_text = _parse_response(raw)
                if response_text:
                    return response_text
                # Empty response — retry if attempts remain
                if attempt < max_retries:
                    continue
            except Exception as exc:
                last_exc = exc
                if attempt < max_retries:
                    continue
                raise
        if last_exc is not None:
            raise last_exc
        return ""

    return _call


def grok_callback(
    model: str = "grok-3",
    api_key: Optional[str] = None,
) -> LLMCallback:
    """Create a callback that uses xAI Grok via OpenAI-compatible API.

    Args:
        model: Grok model ID.
        api_key: xAI API key. Falls back to XAI_API_KEY env var.

    Returns:
        LLM callback function.
    """
    return openai_callback(
        model=model,
        api_key=api_key or os.environ.get("XAI_API_KEY"),
        base_url="https://api.x.ai/v1",
    )


def kimi_callback(
    model: str = "moonshot-v1-128k",
    api_key: Optional[str] = None,
) -> LLMCallback:
    """Create a callback that uses Moonshot Kimi via OpenAI-compatible API.

    Args:
        model: Kimi/Moonshot model ID.
        api_key: Moonshot API key. Falls back to MOONSHOT_API_KEY env var.

    Returns:
        LLM callback function.
    """
    return openai_callback(
        model=model,
        api_key=api_key or os.environ.get("MOONSHOT_API_KEY"),
        base_url="https://api.moonshot.ai/v1",
    )


def nvidia_callback(
    model: str = "meta/llama-3.1-70b-instruct",
    api_key: Optional[str] = None,
) -> LLMCallback:
    """Create a callback that uses NVIDIA NIM via OpenAI-compatible API.

    Args:
        model: NVIDIA model ID.
        api_key: NVIDIA API key. Falls back to NVIDIA_API_KEY env var.

    Returns:
        LLM callback function.
    """
    return openai_callback(
        model=model,
        api_key=api_key or os.environ.get("NVIDIA_API_KEY"),
        base_url="https://integrate.api.nvidia.com/v1",
    )


def claude_agent_sdk_callback(
    model: str = "claude-sonnet-4-20250514",
    max_turns: int = 1,
) -> LLMCallback:
    """Create a callback that uses the Claude Agent SDK (claude CLI subprocess).

    Tries to import claude_agent_sdk. If not available, raises ImportError
    so callers can skip gracefully.

    Args:
        model: Model ID to use (passed via --model flag to claude CLI).
        max_turns: Maximum agentic turns (default 1 for single-shot Q&A).

    Returns:
        LLM callback function.

    Raises:
        ImportError: If claude_agent_sdk is not installed.
    """
    try:
        import claude_agent_sdk  # noqa: F401 — presence check only
    except ImportError:
        raise ImportError(
            "claude_agent_sdk not installed. Install with: pip install claude-agent-sdk"
        )

    import shutil
    import subprocess

    def _call(prompt: Union[str, Any]) -> str:
        claude_bin = shutil.which("claude")
        if not claude_bin:
            raise RuntimeError(
                "claude CLI not found on PATH. Install Claude Code to use this callback."
            )

        if _is_adapted_prompt(prompt):
            text_prompt = (
                prompt.messages[-1]["content"] if prompt.messages else str(prompt)
            )
        else:
            text_prompt = str(prompt)

        cmd = [
            claude_bin,
            "--model", model,
            "--max-turns", str(max_turns),
            "--print",
            text_prompt,
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            raise RuntimeError(
                f"claude CLI exited with code {result.returncode}: {result.stderr.strip()}"
            )

        return result.stdout.strip()

    return _call


def passthrough_callback() -> LLMCallback:
    """Create a callback that returns the prompt unchanged.

    Useful for debugging, testing, or when you want to capture
    the generated prompt for external processing.

    Returns:
        LLM callback that echoes the prompt.
    """
    def _call(prompt: str) -> str:
        return prompt

    return _call


def auto_callback() -> Optional[LLMCallback]:
    """Auto-detect the best available LLM callback.

    Checks in order:
      1. claude_agent_sdk installed → claude_agent_sdk_callback
      2. ANTHROPIC_API_KEY → anthropic_callback
      3. XAI_API_KEY → grok_callback
      4. MOONSHOT_API_KEY → kimi_callback
      5. NVIDIA_API_KEY → nvidia_callback
      6. OPENAI_API_KEY → openai_callback
      7. Ollama running locally → ollama_callback
      8. None (no LLM available)

    Returns:
        The best available callback, or None.
    """
    try:
        return claude_agent_sdk_callback()
    except (ImportError, RuntimeError):
        pass

    if os.environ.get("ANTHROPIC_API_KEY"):
        try:
            return anthropic_callback()
        except ImportError:
            pass

    if os.environ.get("XAI_API_KEY"):
        try:
            return grok_callback()
        except ImportError:
            pass

    if os.environ.get("MOONSHOT_API_KEY"):
        try:
            return kimi_callback()
        except ImportError:
            pass

    if os.environ.get("NVIDIA_API_KEY"):
        try:
            return nvidia_callback()
        except ImportError:
            pass

    if os.environ.get("OPENAI_API_KEY"):
        try:
            return openai_callback()
        except ImportError:
            pass

    # Check if Ollama is running
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags")
        with urllib.request.urlopen(req, timeout=2):
            return ollama_callback()
    except Exception:
        pass

    return None
