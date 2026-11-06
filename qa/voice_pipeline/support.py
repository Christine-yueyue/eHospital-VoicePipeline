"""Shared browser helpers for the Voice Notes tests."""

import os
from pathlib import Path

from playwright.sync_api import expect


FRONTEND_URL = os.environ.get("QA_FRONTEND_URL", "http://127.0.0.1:5174")
QA_DIR = Path(__file__).resolve().parent
FIXTURE = QA_DIR / "fixtures" / "pipeline_tone.wav"


def enable_accessibility(page):
    page.goto(FRONTEND_URL, wait_until="domcontentloaded")
    accessibility_button = page.get_by_role("button", name="Enable accessibility")
    accessibility_button.wait_for(state="attached", timeout=15000)
    accessibility_button.evaluate("(element) => element.click()")
    expect(page.get_by_text("Voice Notes v3").first).to_be_visible()


def connect_app(page, server):
    connect_button = page.get_by_role("button", name="Connect server")
    if connect_button.count():
        connect_button.click()
    else:
        page.get_by_role("button", name="Connection settings").click()
    address = page.get_by_label("Server address")
    token = page.get_by_label("App access token")
    address.click()
    address.press("ControlOrMeta+A")
    address.press_sequentially(server["url"])
    token.click()
    token.press("ControlOrMeta+A")
    token.press_sequentially(server["token"])
    page.get_by_role("button", name="Connect", exact=True).click()
    expect(page.get_by_text("Ready when you are")).to_be_visible(timeout=15000)
