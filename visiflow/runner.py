import os
import sys
import time
import json
from pathlib import Path
from typing import Dict, Any, List, Optional

try:
    import yaml
except ImportError:
    yaml = None

from .core import VisiFlowDetector, logger
from .playwright import VisiPlaywrightPage
from .reporter import global_reporter

class VisiFlowYAMLRunner:
    """
    Declarative No-Code Test Runner for VisiFlow.
    Executes automated tests defined in clean YAML or JSON format,
    supporting full visual actions, spatial relative locators, and HTML reporting.
    """
    def __init__(self, test_file: Optional[str] = None):
        self.test_file = test_file
        self.test_data = None
        if test_file:
            self.load_file(test_file)

    def load_file(self, file_path: str):
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Test definition file not found: {file_path}")

        content = path.read_text(encoding="utf-8")
        if path.suffix.lower() in [".yaml", ".yml"]:
            if yaml is None:
                raise ImportError("PyYAML is required to parse YAML files. Install with 'pip install pyyaml'.")
            self.test_data = yaml.safe_load(content)
        elif path.suffix.lower() == ".json":
            self.test_data = json.loads(content)
        else:
            # Try YAML first, then JSON
            try:
                if yaml:
                    self.test_data = yaml.safe_load(content)
                else:
                    self.test_data = json.loads(content)
            except Exception:
                self.test_data = json.loads(content)

    def _normalize_step(self, step_raw: Any) -> Dict[str, Any]:
        """
        Normalize shorthand step definitions into standard dictionary format:
        e.g.:
          - goto: "https://..."
          - click: "Submit"
          - fill: "Username", value: "admin"
          - click: "Delete", right_of: "Alice"
        """
        if not isinstance(step_raw, dict):
            raise ValueError(f"Invalid step format: {step_raw}")

        # If already in standard action/target format
        if "action" in step_raw:
            return step_raw

        step = dict(step_raw)
        known_actions = [
            "goto", "navigate", "open",
            "click", "fill", "type", "press", "key",
            "assert_visible", "assert_not_visible", "assert",
            "wait_for", "wait", "sleep", "screenshot"
        ]

        for act in known_actions:
            if act in step:
                val = step.pop(act)
                step["action"] = act
                if isinstance(val, dict):
                    step.update(val)
                elif isinstance(val, str):
                    if act in ["goto", "navigate", "open"]:
                        step["url"] = val
                    elif act in ["press", "key"]:
                        step["key"] = val
                    elif act in ["sleep"]:
                        step["seconds"] = float(val)
                    elif act in ["screenshot"]:
                        step["path"] = val
                    else:
                        step["target"] = val
                break

        return step

    def execute(
        self,
        headless: Optional[bool] = None,
        report_path: Optional[str] = None,
        browser_type: str = "chromium"
    ) -> bool:
        """
        Execute the loaded declarative test.
        :return: True if all steps passed, False if any step failed.
        """
        if not self.test_data:
            raise ValueError("No test data loaded. Call load_file() first.")

        from playwright.sync_api import sync_playwright

        name = self.test_data.get("name", "VisiFlow Declarative Test")
        description = self.test_data.get("description", "")
        start_url = self.test_data.get("url")
        steps_raw = self.test_data.get("steps", [])
        
        # Viewport config
        vp_config = self.test_data.get("viewport", {"width": 1280, "height": 800})
        viewport = {"width": int(vp_config.get("width", 1280)), "height": int(vp_config.get("height", 800))}

        # Headless setting
        is_headless = headless if headless is not None else self.test_data.get("headless", False)

        # Output report setting
        out_report = report_path or self.test_data.get("report", "visiflow_report.html")

        print("\n" + "=" * 60)
        print(f"[*] VisiFlow E2E Runner: {name}")
        if description:
            print(f"    {description}")
        print("=" * 60)

        total_steps = len(steps_raw)
        passed_steps = 0
        all_success = True
        total_start_time = time.time()

        with sync_playwright() as p:
            browser_launcher = getattr(p, browser_type, p.chromium)
            browser = browser_launcher.launch(headless=is_headless)
            context = browser.new_context(viewport=viewport)
            page = context.new_page()

            visipage = VisiPlaywrightPage(page)

            # Auto-open start_url if specified at top level
            if start_url:
                print(f"[*] Navigating to initial URL: {start_url}")
                page.goto(start_url, wait_until="networkidle", timeout=30000)

            for idx, raw_step in enumerate(steps_raw):
                step = self._normalize_step(raw_step)
                action = step.get("action", "").lower()
                step_num = idx + 1
                step_start = time.time()

                try:
                    if action in ["goto", "navigate", "open"]:
                        url = step.get("url") or step.get("target")
                        print(f"[{step_num}/{total_steps}] GOTO {url} ...", end=" ", flush=True)
                        page.goto(url, wait_until="networkidle", timeout=30000)

                    elif action in ["click"]:
                        target = step.get("target")
                        desc = visipage._format_target_desc(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index")
                        )
                        print(f"[{step_num}/{total_steps}] CLICK {desc} ...", end=" ", flush=True)
                        visipage.visual_click(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index"),
                            timeout_ms=int(step.get("timeout_ms", 10000))
                        )

                    elif action in ["fill", "type"]:
                        target = step.get("target")
                        val = str(step.get("value", ""))
                        desc = visipage._format_target_desc(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index")
                        )
                        print(f"[{step_num}/{total_steps}] FILL {desc} -> '{val}' ...", end=" ", flush=True)
                        visipage.visual_fill(
                            target,
                            val,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index"),
                            timeout_ms=int(step.get("timeout_ms", 10000))
                        )

                    elif action in ["press", "key"]:
                        key = step.get("key") or step.get("target")
                        print(f"[{step_num}/{total_steps}] PRESS '{key}' ...", end=" ", flush=True)
                        visipage.visual_press(key)

                    elif action in ["assert_visible", "assert"]:
                        target = step.get("target")
                        desc = visipage._format_target_desc(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index")
                        )
                        print(f"[{step_num}/{total_steps}] ASSERT_VISIBLE '{desc}' ...", end=" ", flush=True)
                        visipage.visual_assert_visible(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index"),
                            timeout_ms=int(step.get("timeout_ms", 10000))
                        )

                    elif action in ["assert_not_visible"]:
                        target = step.get("target")
                        desc = visipage._format_target_desc(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index")
                        )
                        print(f"[{step_num}/{total_steps}] ASSERT_NOT_VISIBLE '{desc}' ...", end=" ", flush=True)
                        visipage.visual_assert_not_visible(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index"),
                            timeout_ms=int(step.get("timeout_ms", 5000))
                        )

                    elif action in ["wait_for", "wait"]:
                        target = step.get("target")
                        print(f"[{step_num}/{total_steps}] WAIT_FOR '{target}' ...", end=" ", flush=True)
                        visipage.visual_wait_for(
                            target,
                            right_of=step.get("right_of"),
                            left_of=step.get("left_of"),
                            below=step.get("below"),
                            above=step.get("above"),
                            index=step.get("index"),
                            timeout_ms=int(step.get("timeout_ms", 10000))
                        )

                    elif action in ["sleep"]:
                        dur = float(step.get("seconds", 1.0))
                        print(f"[{step_num}/{total_steps}] SLEEP {dur}s ...", end=" ", flush=True)
                        page.wait_for_timeout(int(dur * 1000))

                    elif action in ["screenshot"]:
                        shot_path = step.get("path") or step.get("target", "screenshot.png")
                        print(f"[{step_num}/{total_steps}] SCREENSHOT -> '{shot_path}' ...", end=" ", flush=True)
                        page.screenshot(path=shot_path)

                    else:
                        raise ValueError(f"Unknown action '{action}'")

                    dur_s = time.time() - step_start
                    print(f"[OK] ({dur_s:.1f}s)")
                    passed_steps += 1

                except Exception as e:
                    dur_s = time.time() - step_start
                    print(f"[FAILED] ({dur_s:.1f}s)")
                    print(f"    --> Error: {e}")
                    all_success = False
                    break

            browser.close()

        # Generate HTML report
        if out_report:
            global_reporter.generate_html_report(out_report)

        total_dur = time.time() - total_start_time
        print("-" * 60)
        if all_success:
            print(f"[PASS] All {passed_steps}/{total_steps} steps passed in {total_dur:.1f}s!")
        else:
            print(f"[FAIL] Test failed at step {passed_steps + 1}/{total_steps} after {total_dur:.1f}s.")
        
        if out_report:
            print(f"[*] Self-Healing HTML Report: {out_report}")
        print("=" * 60 + "\n")

        return all_success
