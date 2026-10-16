import asyncio
import os
import sys
import threading
import time
import uuid
from pathlib import Path
import pytest
import uvicorn
from playwright.async_api import async_playwright

backend_path = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_path))

from app.main import app


class UvicornServer:
    def __init__(self, host="127.0.0.1", port=8888):
        self.host = host
        self.port = port
        self.server = None
        self.thread = None

    def start(self):
        config = uvicorn.Config(app=app, host=self.host, port=self.port, log_level="warning")
        self.server = uvicorn.Server(config)
        self.thread = threading.Thread(target=self.server.run, daemon=True)
        self.thread.start()
        # Wait until server is listening
        for _ in range(50):
            if self.server.started:
                break
            time.sleep(0.1)

    def stop(self):
        if self.server:
            self.server.should_exit = True
            if self.thread and self.thread.is_alive():
                self.thread.join(timeout=3)


@pytest.mark.asyncio
async def test_frontend_full_ui_playwright():
    """Verify React SPA in Chromium via Playwright:
    1. Loads landing page & verifies branding elements
    2. Opens Auth modal & registers a student
    3. Verifies navigation tabs (Roadmap, Notes, Schedule, Community)
    4. Navigates through tabs and verifies reactive UI panels
    5. Captures screenshot artifact
    """
    server = UvicornServer(port=8888)
    server.start()

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(viewport={"width": 1280, "height": 800})
            page = await context.new_page()

            page.on("console", lambda msg: print(f"[CONSOLE {msg.type}] {msg.text}"))
            page.on("pageerror", lambda exc: print(f"[PAGE ERROR] {exc}"))

            # 1. Load Homepage
            await page.goto("http://127.0.0.1:8888", wait_until="networkidle")
            title = await page.title()
            assert "LearnWeave" in title or (await page.locator("text=LearnWeave").count()) > 0

            # 2. Check Branding & Hero
            heading = page.locator("h2")
            await heading.first.wait_for(state="visible", timeout=10000)
            heading_text = await heading.first.inner_text()
            assert "Deep, Long-Term Mastery" in heading_text or "LearnWeave" in heading_text

            # 3. Open Auth Modal
            sign_in_btn = page.locator("button:has-text('Sign In')")
            await sign_in_btn.first.click()

            # Switch to Sign Up tab in modal
            sign_up_toggle = page.locator("button:has-text('Sign Up')")
            await sign_up_toggle.wait_for(state="visible", timeout=5000)
            await sign_up_toggle.click()

            # Fill registration form
            unique_email = f"playwright_{uuid.uuid4().hex[:6]}@example.com"
            name_input = page.locator("input[placeholder*='Ada']")
            await name_input.wait_for(state="visible", timeout=5000)
            await name_input.fill("Playwright Tester")

            await page.locator("input[type='email']").fill(unique_email)
            await page.locator("input[type='password']").fill("SecurePass123!")

            # Submit registration
            submit_auth = page.locator("button[type='submit']")
            await submit_auth.click()

            # Wait for authenticated state (New Goal button visible)
            new_goal_btn = page.locator("button:has-text('New Goal')")
            await new_goal_btn.wait_for(state="visible", timeout=10000)

            # 4. Verify Navigation Tabs (Scoped to nav header)
            notes_tab = page.locator("nav button:has-text('Notes & RAG')")
            schedule_tab = page.locator("nav button:has-text('Schedule')")
            community_tab = page.locator("nav button:has-text('Community')")
            roadmap_tab = page.locator("nav button:has-text('Roadmap')")

            assert await notes_tab.is_visible()
            assert await schedule_tab.is_visible()
            assert await community_tab.is_visible()
            assert await roadmap_tab.is_visible()

            # 5. Navigate to Notes tab
            await page.wait_for_timeout(400)
            await notes_tab.click(force=True)
            await page.locator("text=Study Notes & Hybrid RAG Index").wait_for(state="visible", timeout=5000)
            assert await page.locator("text=Upload Document").is_visible()

            # 6. Navigate to Community tab
            await page.wait_for_timeout(400)
            await community_tab.click(force=True)
            await page.locator("text=Global Community Library").wait_for(state="visible", timeout=5000)
            assert await page.locator("text=Wilson Ranked").is_visible()

            # 7. Navigate to Schedule tab
            await page.wait_for_timeout(400)
            await schedule_tab.click(force=True)
            await page.locator("text=No Active Roadmap").wait_for(state="visible", timeout=5000)

            # 8. Return to Roadmap tab
            await page.wait_for_timeout(400)
            await roadmap_tab.click(force=True)

            # Capture UI Screenshot Artifact
            artifacts_dir = Path(__file__).resolve().parent.parent / "evals" / "results"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            screenshot_path = artifacts_dir / "ui_dashboard.png"
            await page.screenshot(path=str(screenshot_path))
            assert screenshot_path.exists()
            assert screenshot_path.stat().st_size > 1000

            await browser.close()
    finally:
        server.stop()
