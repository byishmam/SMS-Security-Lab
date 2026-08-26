"""
SMS Security Lab — local-only SMS delivery simulator.

This application NEVER sends real SMS messages and NEVER makes any
outbound network request. Every "delivery" is a purely in-memory,
random-outcome simulation used to teach the shape of a typical
SMS-sending backend (API -> provider abstraction -> delivery event ->
inbox -> logging) without touching any real telecom infrastructure.

Design constraints (intentional, do not relax):
  - Exactly ONE simulated message is created per POST /api request.
  - There is no bulk-send, count, repeat, or batch endpoint/parameter.
  - SmsProvider.send_message() never opens a socket or HTTP connection.
  - No provider credentials, API keys, or gateway config exist anywhere.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from datetime import datetime
from itertools import count
from threading import Lock
from typing import Any

from flask import Flask, jsonify, render_template, request

app = Flask(__name__)

MAX_MESSAGE_LENGTH = 320
DELIVERY_SUCCESS_PROBABILITY = 0.95  # 95% delivered, 5% failed (for demo purposes)

# A conservative "looks like a phone number" check — digits only,
# optional leading '+', 8-15 digits. This is intentionally superficial;
# it exists to reject obviously-invalid input, not to validate real numbers.
PHONE_PATTERN = re.compile(r"^\+?\d{8,15}$")

_id_counter = count(1)
_state_lock = Lock()


def mask_phone_number(number: str) -> str:
    """Mask all but the first 3 and last 2 digits of a phone number.

    Example: 8801712345678 -> 880********78
    Numbers too short to mask meaningfully are mostly starred out.
    """
    digits = number.strip()
    if len(digits) <= 5:
        return "*" * len(digits)
    head = digits[:3]
    tail = digits[-2:]
    middle = "*" * (len(digits) - len(head) - len(tail))
    return f"{head}{middle}{tail}"


def next_message_id() -> str:
    """Generate a simple, demonstrable sequential message id."""
    n = next(_id_counter)
    date_part = datetime.now().strftime("%Y%m%d")
    return f"id-{date_part}-{n:04d}"


@dataclass
class LabState:
    """All application state, held in memory only. Lost on restart."""

    inbox: list[dict[str, Any]] = field(default_factory=list)
    events: list[dict[str, Any]] = field(default_factory=list)
    attempts: int = 0
    delivered: int = 0
    failed: int = 0

    def stats(self) -> dict[str, int]:
        return {
            "attempts": self.attempts,
            "delivered": self.delivered,
            "failed": self.failed,
            "messages": len(self.inbox),
        }

    def clear(self) -> None:
        self.inbox.clear()
        self.events.clear()
        self.attempts = 0
        self.delivered = 0
        self.failed = 0


state = LabState()


class SmsProvider:
    """Local SMS provider.

    This class simulates the *interface* of a real SMS gateway client
    (a `send_message` method returning a delivery result) without ever
    performing any network I/O, without any credentials, and without
    any external dependency. It exists purely so the rest of the app
    can be structured the way a real integration would be, for
    teaching purposes.
    """

    NAME = "LOCAL-PROVIDER"

    def send_message(self, recipient: str, message: str) -> dict[str, Any]:
        """Simulate sending a single SMS and return a delivery result.

        No network request is made. The outcome is decided locally by
        a weighted coin flip so the demo can show both success and
        failure states.
        """
        delivered = random.random() < DELIVERY_SUCCESS_PROBABILITY
        return {
            "success": delivered,
            "provider": self.NAME,
            "message_id": next_message_id(),
            "status": "DELIVERED" if delivered else "FAILED",
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "recipient": recipient,
        }


provider = SmsProvider()


def validate_input(number: str | None, message: str | None) -> str | None:
    """Return an error string if input is invalid, else None."""
    if not number or not number.strip():
        return "Please enter a recipient."
    if not message or not message.strip():
        return "Please enter a message."
    if len(message) > MAX_MESSAGE_LENGTH:
        return f"Message must be {MAX_MESSAGE_LENGTH} characters or fewer."
    if not PHONE_PATTERN.match(number.strip()):
        return "Please enter a valid-looking phone number."
    return None


@app.route("/")
def index():
    """Serve the dashboard frontend."""
    return render_template("index.html")


@app.route("/api", methods=["POST"])
def api_send():
    """Handle a single simulated SMS send request.

    Creates exactly one simulated delivery event per request. There is
    intentionally no way to send more than one message per call.
    """
    payload = request.get_json(silent=True) or {}
    number = str(payload.get("number", "")).strip()
    message = str(payload.get("message", "")).strip()

    error = validate_input(number, message)
    if error:
        return jsonify({"ok": False, "error": error}), 400

    with _state_lock:
        result = provider.send_message(number, message)
        state.attempts += 1

        masked = mask_phone_number(number)
        event = {
            "timestamp": result["timestamp"],
            "mode": "TEST",
            "recipient_masked": masked,
            "status": result["status"],
            "message_id": result["message_id"],
            "provider": result["provider"],
        }
        state.events.insert(0, event)

        if result["success"]:
            state.delivered += 1
            inbox_item = {
                "sender": "SMS Service",
                "timestamp": result["timestamp"],
                "recipient_masked": masked,
                "message": message,
                "status": result["status"],
                "message_id": result["message_id"],
                "label": "Test SMS",
            }
            state.inbox.insert(0, inbox_item)
        else:
            state.failed += 1

        response = {
            "ok": True,
            "event": event,
            "stats": state.stats(),
            "inbox": state.inbox,
        }

    return jsonify(response)


@app.route("/api/state", methods=["GET"])
def api_state():
    """Return the full current lab state."""
    with _state_lock:
        return jsonify(
            {
                "events": state.events,
                "inbox": state.inbox,
                "stats": state.stats(),
            }
        )


@app.route("/api/clear", methods=["POST"])
def api_clear():
    """Clear all in-memory lab data (inbox, events, statistics)."""
    with _state_lock:
        state.clear()
    return jsonify({"ok": True})


@app.errorhandler(404)
def not_found(_err):
    return jsonify({"ok": False, "error": "Not found."}), 404


@app.errorhandler(500)
def server_error(_err):
    # Never expose stack traces to the client.
    return jsonify({"ok": False, "error": "Internal server error."}), 500


if __name__ == "__main__":
    # Local educational use only: bind to loopback so the app is not
    # reachable from other machines on the network.
    app.run(host="127.0.0.1", port=5000, debug=True)
