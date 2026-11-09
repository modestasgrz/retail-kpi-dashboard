"""ADAPT: wire the kit's security tests (test_security.py) to this app. Owner-only, locked like tests/acceptance/.

Fill every function and constant marked ADAPT. A check that genuinely doesn't apply goes in NOT_APPLICABLE with
the reason; it then shows as skipped with that reason. Never use NOT_APPLICABLE to silence a failing check; a real hole the owner accepts
for now goes in KNOWN_OPEN (shows as xfail with the reason).
Check names: pii_logs, prompt_injection, model_output, step_skip, xff_spoof, cors, provider_error, body_cap, image_lock.
`make security` fails when a test listed in tests/security/EXPECTED_TESTS isn't collected by the full test run.
After adapting: uv run pytest tests/security --collect-only -q | grep '::' > tests/security/EXPECTED_TESTS
"""

from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import pytest
from starlette.testclient import TestClient

if TYPE_CHECKING:
    from kit_security import FakeLLM

REPO = Path(__file__).resolve().parents[2]

NOT_APPLICABLE: dict[str, str] = {
    "pii_logs": "no visitor text or email input: the only inputs are fixed-choice filters, and the committed data has no customer ids or other personal fields",
    "prompt_injection": "no language model is called at runtime",
    "model_output": "no language model is called at runtime; saved summaries are static committed text",
    "step_skip": "read-only dashboard, no multi-step workflow and no writes",
    "xff_spoof": "no rate-limited endpoint of our own; Streamlit serves the page and nothing is metered",
    "cors": "no API endpoint of our own; Streamlit serves the page only",
    "provider_error": "no outside provider is called at runtime",
    "body_cap": "no POST endpoint of our own; inputs are fixed-choice widgets",
    "image_lock": "no deploy image built by this repo; the hosted app installs from requirements.txt exported from uv.lock",
}
# A real hole the owner accepts for now (shows as xfail with the reason, listed in the PR). Fix it, then remove the entry.
KNOWN_OPEN: dict[str, str] = {}

RATE_LIMIT = 5  # ADAPT: requests one session may make to the rate-limited endpoint before it gets 429
CORS_PATH = "/ADAPT"  # ADAPT: a route browsers call cross-origin
ALLOWED_ORIGIN = "https://ADAPT.example"  # ADAPT: the one origin allowed to call it
BODY_CAP_PATH = "/ADAPT"  # ADAPT: a POST route that takes a JSON body
REQUEST_ID_HEADER = "x-request-id"
USER_INPUT_TAG = "user_input"  # ADAPT: tag the app fences visitor text in, e.g. <user_input> or <visitor_input name="...">
# ADAPT: files that define deploy images, e.g. [REPO / "api" / "app.py"]
IMAGE_FILES: list[Path] = []


def app() -> Any:
    """No HTTP app of our own: an empty ASGI app so the shared fixtures build; every check is n/a above."""
    from starlette.applications import Starlette

    return Starlette()


def install_fakes(monkeypatch: pytest.MonkeyPatch, llm: "FakeLLM") -> None:
    """No outside services exist at runtime: nothing to fake."""


def good_reply() -> Any:
    """ADAPT: a valid model reply the app accepts (what llm.respond returns by default)."""
    return ""


def invalid_reply(canary: str) -> Any:
    """ADAPT: a model reply that breaks the app's output schema and contains canary, e.g. {"questions": canary}."""
    raise NotImplementedError(
        "ADAPT tests/security/security_adapter.py: invalid_reply()"
    )


def provider_error(canary: str) -> Exception:
    """ADAPT: the error the provider SDK raises on a 5xx, with canary in its message/body."""
    return RuntimeError(f"provider 500: {canary}")


def send_visitor_text(http: TestClient, text: str, email: str) -> Any:
    """ADAPT: run the full visitor flow that reaches the model, with text in EVERY free-text field and email where
    the app takes one. Return the response of the request that calls the model."""
    raise NotImplementedError(
        "ADAPT tests/security/security_adapter.py: send_visitor_text()"
    )


def skip_step(http: TestClient) -> Any:
    """ADAPT: call a later workflow step directly, without the server-side state its earlier step creates."""
    raise NotImplementedError("ADAPT tests/security/security_adapter.py: skip_step()")


def writes() -> list[Any]:
    """ADAPT: what the in-memory fakes from install_fakes stored (sheet rows, emails...)."""
    raise NotImplementedError("ADAPT tests/security/security_adapter.py: writes()")


def call_rate_limited(http: TestClient, headers: dict[str, str]) -> Any:
    """ADAPT: one call to the rate-limited endpoint in the same visitor session, with these extra headers."""
    raise NotImplementedError(
        "ADAPT tests/security/security_adapter.py: call_rate_limited()"
    )


BREAK_DEPENDENCY: dict[str, Callable[[pytest.MonkeyPatch], None]] = {}
"""ADAPT: one entry per outside service the flow writes to, making it raise, e.g.
{"sheet": lambda mp: mp.setattr(app_module, "append_row", raise_error)}. PII must stay out of the logs when it fails."""
