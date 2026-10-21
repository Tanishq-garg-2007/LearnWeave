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
            page.on("response", lambda res: print(f"[HTTP {res.status}] {res.url}") if res.status >= 400 else None)

            # 1. Load Homepage
            await page.goto("http://127.0.0.1:8888", wait_until="networkidle")
            title = await page.title()
            assert "LearnWeave" in title or (await page.locator("text=LearnWeave").count()) > 0

            # 2. Check Branding & Hero
            heading = page.locator("h1, h2")
            await heading.first.wait_for(state="visible", timeout=10000)
            heading_text = await heading.first.inner_text()
            assert "Collaborative Learning" in heading_text or "LearnWeave" in heading_text or "Deep, Long-Term Mastery" in heading_text

            # 3. Open Registration
            await page.goto("http://127.0.0.1:8888/register", wait_until="networkidle")

            # Fill registration form
            unique_email = f"playwright_{uuid.uuid4().hex[:6]}@example.com"
            name_input = page.locator("input[placeholder*='Ada'], input[placeholder*='name'], input[id='fullname'], input[type='text']")
            if await name_input.count() > 0:
                await name_input.first.fill("Playwright Tester")

            await page.locator("input[id='register-email'], input[type='email']").first.fill(unique_email)
            await page.locator("input[id='register-password'], input[type='password']").first.fill("SecurePass123!")
            confirm_pwd = page.locator("input[id='register-confirm-password'], input[id='confirm-password'], input[placeholder*='Confirm']")
            if await confirm_pwd.count() > 0:
                await confirm_pwd.first.fill("SecurePass123!")

            # Submit registration
            submit_auth = page.locator("button[type='submit']")
            await submit_auth.click()

            # Wait for authenticated state (New Goal button visible)
            new_goal_btn = page.locator("button:has-text('New Goal'), a:has-text('New Goal')")
            await new_goal_btn.first.wait_for(state="visible", timeout=10000)

            # 4. Verify Navigation Tabs (Scoped to nav header)
            notes_tab = page.locator("nav a:has-text('Notes'), nav button:has-text('Notes')")
            schedule_tab = page.locator("nav a:has-text('Schedule'), nav button:has-text('Schedule')")
            community_tab = page.locator("nav a:has-text('Community'), nav button:has-text('Community')")
            roadmap_tab = page.locator("nav a:has-text('Roadmap'), nav button:has-text('Roadmap')")

            assert await notes_tab.first.is_visible()
            assert await schedule_tab.first.is_visible()
            assert await community_tab.first.is_visible()
            assert await roadmap_tab.first.is_visible()

            # 5. Navigate to Notes tab
            await page.wait_for_timeout(400)
            await notes_tab.first.click(force=True)
            await page.locator("text=Study Notes").first.wait_for(state="visible", timeout=8000)
            assert (await page.locator("text=Upload").count()) > 0 or (await page.locator("text=Ingested Documents").count()) > 0

            # 6. Navigate to Community tab
            await page.wait_for_timeout(400)
            await community_tab.first.click(force=True)
            community_heading = page.get_by_text("Community Learning Library")
            await community_heading.first.wait_for(state="visible", timeout=10000)
            assert (await page.locator("text=Wilson").count()) > 0 or (await page.locator("text=Library").count()) > 0

            # 7. Navigate to Schedule tab
            await page.wait_for_timeout(400)
            await schedule_tab.first.click(force=True)
            schedule_heading = page.get_by_text("Adaptive Study Planner")
            await schedule_heading.first.wait_for(state="visible", timeout=10000)
            assert await schedule_heading.first.is_visible()

            # 8. Return to Roadmap tab
            await page.wait_for_timeout(400)
            await roadmap_tab.first.click(force=True)
            await page.wait_for_timeout(600)

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
