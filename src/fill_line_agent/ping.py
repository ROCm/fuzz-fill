# Copyright Advanced Micro Devices, Inc.
# SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
"""Send one prompt through the LLM gateway to check the Agent SDK setup.

The subscription key and gateway base URL are never printed.

    python -m fill_line_agent.ping --api-key … --base-url … --user-ntid …
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path

API_KEY_ENV = "FUZZ_FILL_API_KEY"
BASE_URL_ENV = "FUZZ_FILL_BASE_URL"
USER_NTID_ENV = "USER_NTID"

GATEWAY_MODEL_ENV = {
    "ANTHROPIC_AUTH_TOKEN": "placeholder",
    "ANTHROPIC_MODEL": "sonnet",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "Claude-Opus-4.7",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "Claude-Sonnet-4.6",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "Claude-Haiku-4.5",
}


def _read_secret_file(path: Path, *, label: str) -> str:
    text = path.read_text(encoding="utf-8").strip()
    if not text:
        raise SystemExit(f"{path}: {label} file is empty")
    return text


def load_api_key(path: Path) -> str:
    """Read a subscription key from ``path`` without echoing it."""
    return _read_secret_file(path, label="key")


def resolve_api_key(*, api_key: str | None = None, key_file: Path | None = None) -> str:
    """Return a subscription key from ``--api-key``, ``--key-file``, or env."""
    if api_key is not None and key_file is not None:
        raise SystemExit("pass only one of --api-key or --key-file")
    if api_key is not None:
        key = api_key.strip()
        if not key:
            raise SystemExit("--api-key is empty")
        return key
    if key_file is not None:
        path = key_file.expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"key file not found: {path}")
        return load_api_key(path)
    env_key = os.environ.get(API_KEY_ENV, "").strip()
    if env_key:
        return env_key
    raise SystemExit(
        f"pass --api-key, --key-file, or set the {API_KEY_ENV} environment variable"
    )


def resolve_base_url(
    *, base_url: str | None = None, base_url_file: Path | None = None
) -> str:
    """Return the gateway base URL from ``--base-url``, ``--base-url-file``, or env."""
    if base_url is not None and base_url_file is not None:
        raise SystemExit("pass only one of --base-url or --base-url-file")
    if base_url is not None:
        url = base_url.strip()
        if not url:
            raise SystemExit("--base-url is empty")
        return url
    if base_url_file is not None:
        path = base_url_file.expanduser().resolve()
        if not path.is_file():
            raise SystemExit(f"base-url file not found: {path}")
        return _read_secret_file(path, label="base-url")
    env_url = os.environ.get(BASE_URL_ENV, "").strip()
    if env_url:
        return env_url
    raise SystemExit(
        f"pass --base-url, --base-url-file, or set the {BASE_URL_ENV} environment variable"
    )


def add_api_key_arguments(parser: argparse.ArgumentParser) -> None:
    key = parser.add_mutually_exclusive_group(required=False)
    key.add_argument(
        "--key-file",
        type=Path,
        help="File whose contents are the LLM gateway subscription key",
    )
    key.add_argument(
        "--api-key",
        help=f"LLM gateway subscription key (or set {API_KEY_ENV})",
    )


def add_base_url_arguments(parser: argparse.ArgumentParser) -> None:
    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument(
        "--base-url-file",
        type=Path,
        help="File whose contents are the LLM gateway base URL",
    )
    group.add_argument(
        "--base-url",
        help=f"LLM gateway base URL (or set {BASE_URL_ENV})",
    )


def resolve_user_ntid(*, user_ntid: str | None = None) -> str:
    """Return the NTID from ``--user-ntid`` or env."""
    if user_ntid is not None:
        value = user_ntid.strip()
        if not value:
            raise SystemExit("--user-ntid is empty")
        return value
    env_value = os.environ.get(USER_NTID_ENV, "").strip()
    if env_value:
        return env_value
    raise SystemExit(
        f"pass --user-ntid or set the {USER_NTID_ENV} environment variable"
    )


def add_user_ntid_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--user-ntid",
        help=f"NTID for the gateway user header (or set {USER_NTID_ENV})",
    )


_REDACTED = "<redacted>"
_secret_filter: logging.Filter | None = None


class _SecretRedactFilter(logging.Filter):
    """Replace known secrets in every log record's formatted message."""

    def __init__(self, secrets: tuple[str, ...]) -> None:
        super().__init__()
        self._secrets = tuple(sorted({s for s in secrets if s}, key=len, reverse=True))

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._secrets:
            return True
        try:
            message = record.getMessage()
        except Exception:
            return True
        redacted = message
        for secret in self._secrets:
            if secret in redacted:
                redacted = redacted.replace(secret, _REDACTED)
        if redacted != message:
            record.msg = redacted
            record.args = ()
        return True


def install_secret_redaction(*secrets: str) -> None:
    """Ensure *secrets* never appear in process logs (stderr, log files, etc.)."""
    global _secret_filter
    cleaned = tuple(s.strip() for s in secrets if s and s.strip())
    if not cleaned:
        return
    new_filter = _SecretRedactFilter(cleaned)
    targets: list[logging.Logger] = [
        logging.getLogger(),
        logging.getLogger("fuzz_fill"),
        logging.getLogger("claude_agent_sdk"),
    ]
    for logger in targets:
        if _secret_filter is not None:
            logger.removeFilter(_secret_filter)
            for handler in logger.handlers:
                handler.removeFilter(_secret_filter)
        logger.addFilter(new_filter)
        for handler in logger.handlers:
            handler.addFilter(new_filter)
    _secret_filter = new_filter
    for i, arg in enumerate(sys.argv):
        for secret in cleaned:
            if secret in arg:
                sys.argv[i] = arg.replace(secret, _REDACTED)


def gateway_settings(*, api_key: str, base_url: str, user_ntid: str) -> str:
    headers = "\n".join(
        [
            f"Ocp-Apim-Subscription-Key: {api_key}",
            f"user: {user_ntid}",
        ]
    )
    env = {
        **GATEWAY_MODEL_ENV,
        "ANTHROPIC_BASE_URL": base_url,
        "ANTHROPIC_CUSTOM_HEADERS": headers,
    }
    return json.dumps({"env": env})


async def run(
    prompt: str,
    *,
    api_key: str,
    base_url: str,
    user_ntid: str,
    quiet: bool = False,
) -> int:
    """Return 0 if the gateway answers; 1 on failure.

    When *quiet* is true, do not print the model reply (used by fill-line preflight).
    """
    try:
        from claude_agent_sdk import (
            AssistantMessage,
            ClaudeAgentOptions,
            ResultMessage,
            query,
        )
    except ImportError:
        print(
            "claude-agent-sdk is not installed. Install it with: pip install claude-agent-sdk",
            file=sys.stderr,
        )
        return 1

    options = ClaudeAgentOptions(
        setting_sources=[],
        settings=gateway_settings(
            api_key=api_key, base_url=base_url, user_ntid=user_ntid
        ),
        tools=[],
        max_turns=1,
        permission_mode="dontAsk",
        thinking={"type": "disabled"},
    )
    saw_text = False
    failed = False
    reply_parts: list[str] = []
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                text = getattr(block, "text", None)
                if text:
                    saw_text = True
                    reply_parts.append(text)
                    if not quiet:
                        print(text, end="" if text.endswith("\n") else "\n")
        elif isinstance(message, ResultMessage):
            if message.is_error:
                failed = True
                print(f"error: {message.subtype}", file=sys.stderr)
            elif not quiet:
                print(f"done: {message.subtype}", file=sys.stderr)
    if failed or not saw_text:
        return 1
    if quiet:
        joined = "".join(reply_parts).strip().lower()
        if "pong" not in joined:
            print(f"gateway ping unexpected reply: {joined!r}", file=sys.stderr)
            return 1
    return 0


async def ping_gateway(*, api_key: str, base_url: str, user_ntid: str) -> None:
    """Raise ``RuntimeError`` if the LLM gateway does not answer ``pong``."""
    rc = await run(
        "Reply with exactly the word pong and nothing else.",
        api_key=api_key,
        base_url=base_url,
        user_ntid=user_ntid,
        quiet=True,
    )
    if rc != 0:
        raise RuntimeError("gateway ping failed")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    add_api_key_arguments(parser)
    add_base_url_arguments(parser)
    add_user_ntid_arguments(parser)
    parser.add_argument(
        "--prompt",
        default="Reply with exactly the word pong and nothing else.",
    )
    args = parser.parse_args()
    api_key = resolve_api_key(api_key=args.api_key, key_file=args.key_file)
    base_url = resolve_base_url(base_url=args.base_url, base_url_file=args.base_url_file)
    user_ntid = resolve_user_ntid(user_ntid=args.user_ntid)
    install_secret_redaction(api_key, base_url, user_ntid)
    if args.api_key is not None:
        args.api_key = _REDACTED
    if args.base_url is not None:
        args.base_url = _REDACTED
    if args.user_ntid is not None:
        args.user_ntid = _REDACTED
    raise SystemExit(
        asyncio.run(
            run(
                args.prompt,
                api_key=api_key,
                base_url=base_url,
                user_ntid=user_ntid,
            )
        )
    )


if __name__ == "__main__":
    main()
