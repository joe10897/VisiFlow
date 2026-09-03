import os
import sys
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional
import xml.etree.ElementTree as ET
from concurrent.futures import ProcessPoolExecutor, as_completed

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
    supporting visual actions, spatial relative locators, smart visual debugging,
    auto-healing, and HTML reporting.
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
            try:
                if yaml:
                    self.test_data = yaml.safe_load(content)
                else:
                    self.test_data = json.loads(content)
            except Exception:
                self.test_data = json.loads(content)

    def save_file(self):
        """Save updated test_data back to disk (used for auto-healing)."""
        if not self.test_file or not self.test_data:
            return
        path = Path(self.test_file)
        if path.suffix.lower() in [".yaml", ".yml"] and yaml:
            with open(path, "w", encoding="utf-8") as f:
                yaml.dump(self.test_data, f, sort_keys=False, allow_unicode=True)
        elif path.suffix.lower() == ".json":
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.test_data, f, indent=2, ensure_ascii=False)

    def _normalize_step(self, step_raw: Any) -> Dict[str, Any]:
        if not isinstance(step_raw, dict):
            raise ValueError(f"Invalid step format: {step_raw}")

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
        browser_type: str = "chromium",
        auto_heal: bool = False,
        interactive: bool = False
    ) -> Dict[str, Any]:
        """
        Execute the declarative test with smart visual debugging and auto-healing.
        :return: Dict summarizing test execution and step records.
        """
        if not self.test_data:
            raise ValueError("No test data loaded. Call load_file() first.")

        from playwright.sync_api import sync_playwright

        name = self.test_data.get("name", "VisiFlow Declarative Test")
        description = self.test_data.get("description", "")
        start_url = self.test_data.get("url")
        steps_raw = self.test_data.get("steps", [])
        
        vp_config = self.test_data.get("viewport", {"width": 1280, "height": 800})
        viewport = {"width": int(vp_config.get("width", 1280)), "height": int(vp_config.get("height", 800))}

        is_headless = headless if headless is not None else self.test_data.get("headless", False)
        out_report = report_path or self.test_data.get("report", "visiflow_report.html")

        print("\n" + "=" * 60)
        print(f"[*] VisiFlow E2E Runner: {name}")
        if description:
            print(f"    {description}")
        print("=" * 60)

        total_steps = len(steps_raw)
        passed_steps = 0
        all_success = True
        step_records = []
        total_start_time = time.time()

        with sync_playwright() as p:
            browser_launcher = getattr(p, browser_type, p.chromium)
            browser = browser_launcher.launch(headless=is_headless)
            context = browser.new_context(viewport=viewport)
            page = context.new_page()

            visipage = VisiPlaywrightPage(page)

            if start_url:
                print(f"[*] Navigating to initial URL: {start_url}")
                page.goto(start_url, wait_until="networkidle", timeout=30000)

            for idx, raw_step in enumerate(steps_raw):
                step = self._normalize_step(raw_step)
                action = step.get("action", "").lower()
                step_num = idx + 1
                step_start = time.time()
                step_desc = ""

                try:
                    if action in ["goto", "navigate", "open"]:
                        url = step.get("url") or step.get("target")
                        step_desc = f"GOTO {url}"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
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
                        step_desc = f"CLICK {desc}"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
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
                        step_desc = f"FILL {desc} -> '{val}'"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
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
                        step_desc = f"PRESS '{key}'"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
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
                        step_desc = f"ASSERT_VISIBLE '{desc}'"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
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
                        step_desc = f"ASSERT_NOT_VISIBLE '{desc}'"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
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
                        step_desc = f"WAIT_FOR '{target}'"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
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
                        step_desc = f"SLEEP {dur}s"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
                        page.wait_for_timeout(int(dur * 1000))

                    elif action in ["screenshot"]:
                        shot_path = step.get("path") or step.get("target", "screenshot.png")
                        step_desc = f"SCREENSHOT -> '{shot_path}'"
                        print(f"[{step_num}/{total_steps}] {step_desc} ...", end=" ", flush=True)
                        page.screenshot(path=shot_path)

                    else:
                        raise ValueError(f"Unknown action '{action}'")

                    dur_s = time.time() - step_start
                    print(f"[OK] ({dur_s:.1f}s)")
                    passed_steps += 1
                    step_records.append({
                        "name": step_desc,
                        "action": action,
                        "time": dur_s,
                        "status": "passed",
                        "error": None
                    })

                except Exception as e:
                    dur_s = time.time() - step_start
                    print(f"[FAILED] ({dur_s:.1f}s)")
                    print(f"    --> Error: {e}")

                    # --- Smart Visual Debugger & Auto-Suggest (Direction C) ---
                    target = step.get("target")
                    suggestions = []
                    debug_img_path = None
                    if target:
                        # 1. Capture current failure state to file
                        fd, temp_fail_img = tempfile.mkstemp(suffix=".png")
                        os.close(fd)
                        try:
                            page.screenshot(path=temp_fail_img)
                            candidates = visipage.detector.get_closest_candidates(target, top_k=3)
                            if candidates:
                                suggestions = [c["text"] for c in candidates]
                                print(f"\n    [SUGGEST] Target '{target}' not found on screen.")
                                print("       Closest visual candidates detected:")
                                for c_idx, c in enumerate(candidates, 1):
                                    print(f"       {c_idx}. '{c['text']}' (similarity: {int(c['score']*100)}%)")

                                # 2. Generate annotated debug diff image
                                report_dir = Path(out_report).parent if out_report else Path(".")
                                debug_img_path = str(report_dir / f"debug_diff_step_{step_num}.png")
                                visipage.detector.generate_visual_debug_diff(temp_fail_img, target, debug_img_path)
                                print(f"       [DIFF] Annotated visual diff saved to: {debug_img_path}")

                                # 3. Auto-Heal or Interactive Prompt
                                best_match = candidates[0]
                                should_heal = False
                                if auto_heal and best_match["score"] >= 0.5:
                                    should_heal = True
                                elif interactive and best_match["score"] >= 0.5:
                                    ans = input(f"       [?] Update '{target}' -> '{best_match['text']}' in test script? [y/N]: ").strip().lower()
                                    if ans == 'y':
                                        should_heal = True

                                if should_heal and self.test_file:
                                    # Update in-memory test step
                                    if "target" in steps_raw[idx]:
                                        steps_raw[idx]["target"] = best_match["text"]
                                    elif action in steps_raw[idx]:
                                        if isinstance(steps_raw[idx][action], str):
                                            steps_raw[idx][action] = best_match["text"]
                                        elif isinstance(steps_raw[idx][action], dict):
                                            steps_raw[idx][action]["target"] = best_match["text"]
                                    self.save_file()
                                    print(f"       [HEALED] Updated step {step_num} in '{self.test_file}' -> '{best_match['text']}'")
                        finally:
                            if os.path.exists(temp_fail_img):
                                os.remove(temp_fail_img)

                    all_success = False
                    step_records.append({
                        "name": step_desc,
                        "action": action,
                        "time": dur_s,
                        "status": "failed",
                        "error": str(e),
                        "suggestions": suggestions,
                        "debug_diff": debug_img_path
                    })
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

        return {
            "file": self.test_file or name,
            "name": name,
            "success": all_success,
            "duration": total_dur,
            "total_steps": total_steps,
            "passed_steps": passed_steps,
            "steps": step_records
        }

def generate_junit_xml(suite_results: List[Dict[str, Any]], output_path: str):
    """
    Generate standard JUnit XML report for CI/CD test dashboards (GitHub Actions, GitLab, Jenkins).
    """
    total_tests = sum(len(s.get("steps", [])) for s in suite_results)
    total_failures = sum(1 for s in suite_results if not s.get("success", False))
    total_time = sum(s.get("duration", 0.0) for s in suite_results)

    testsuites_el = ET.Element("testsuites", {
        "name": "VisiFlow",
        "tests": str(total_tests),
        "failures": str(total_failures),
        "errors": "0",
        "time": f"{total_time:.2f}"
    })

    for suite in suite_results:
        suite_el = ET.SubElement(testsuites_el, "testsuite", {
            "name": suite.get("name", "VisiFlow Suite"),
            "tests": str(len(suite.get("steps", []))),
            "failures": "1" if not suite.get("success") else "0",
            "errors": "0",
            "time": f"{suite.get('duration', 0.0):.2f}"
        })

        for step in suite.get("steps", []):
            tc_el = ET.SubElement(suite_el, "testcase", {
                "name": step.get("name", "Unknown Step"),
                "classname": Path(suite.get("file", "test")).stem,
                "time": f"{step.get('time', 0.0):.2f}"
            })

            if step.get("status") == "failed":
                fail_el = ET.SubElement(tc_el, "failure", {
                    "message": step.get("error") or "Step failed",
                    "type": "AssertionError"
                })
                fail_msg = f"Step Failed: {step.get('name')}\nError: {step.get('error')}\n"
                if step.get("suggestions"):
                    fail_msg += f"Auto-Suggestions: {', '.join(step['suggestions'])}\n"
                if step.get("debug_diff"):
                    fail_msg += f"Visual Diff Screenshot: {step['debug_diff']}\n"
                fail_el.text = fail_msg

    tree = ET.ElementTree(testsuites_el)
    ET.indent(tree, space="  ", level=0)
    tree.write(output_path, encoding="utf-8", xml_declaration=True)
    logger.info(f"JUnit XML test report written to: {output_path}")

def _worker_execute_file(args: Dict[str, Any]) -> Dict[str, Any]:
    """Worker function for executing a single test file in parallel."""
    file_path = args["file_path"]
    headless = args.get("headless", True)
    report_path = args.get("report_path")
    browser_type = args.get("browser_type", "chromium")
    auto_heal = args.get("auto_heal", False)

    runner = VisiFlowYAMLRunner(file_path)
    return runner.execute(
        headless=headless,
        report_path=report_path,
        browser_type=browser_type,
        auto_heal=auto_heal,
        interactive=False
    )

def run_suite(
    target_paths: List[str],
    workers: int = 1,
    headless: Optional[bool] = None,
    report_dir: Optional[str] = None,
    junit_path: Optional[str] = None,
    browser_type: str = "chromium",
    auto_heal: bool = False,
    interactive: bool = False
) -> bool:
    """
    Batch test suite executor supporting multiple files, directories, and parallel worker processes.
    """
    # 1. Discover all test files
    discovered_files = []
    for tp in target_paths:
        p = Path(tp)
        if p.is_dir():
            for ext in ["*.yaml", "*.yml", "*.json"]:
                discovered_files.extend(sorted(p.glob(ext)))
        elif p.is_file():
            discovered_files.append(p)
        else:
            print(f"[WARN] Target path '{tp}' does not exist, skipping.")

    # Remove duplicates
    seen = set()
    test_files = []
    for f in discovered_files:
        sf = str(f.resolve())
        if sf not in seen:
            seen.add(sf)
            test_files.append(str(f))

    if not test_files:
        print("[ERROR] No YAML or JSON test files found to execute.")
        return False

    print("\n" + "=" * 60)
    print(f"[*] VisiFlow Test Suite: Found {len(test_files)} test file(s)")
    print(f"   Workers: {workers} | Headless: {headless} | Browser: {browser_type}")
    print("=" * 60)

    suite_results = []
    start_suite_time = time.time()

    # Prepare worker tasks
    tasks = []
    for f in test_files:
        out_rep = None
        if report_dir:
            out_rep = str(Path(report_dir) / f"{Path(f).stem}_report.html")
        tasks.append({
            "file_path": f,
            "headless": headless if headless is not None else True,
            "report_path": out_rep,
            "browser_type": browser_type,
            "auto_heal": auto_heal
        })

    if workers > 1 and len(test_files) > 1:
        # Parallel Execution
        num_workers = min(workers, len(test_files))
        print(f"[*] Executing in parallel across {num_workers} processes...\n")
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            future_to_file = {executor.submit(_worker_execute_file, t): t["file_path"] for t in tasks}
            for future in as_completed(future_to_file):
                f_name = future_to_file[future]
                try:
                    res = future.result()
                    suite_results.append(res)
                except Exception as exc:
                    print(f"[ERROR] Test execution failed for '{f_name}': {exc}")
                    suite_results.append({
                        "file": f_name,
                        "name": Path(f_name).stem,
                        "success": False,
                        "duration": 0.0,
                        "total_steps": 0,
                        "passed_steps": 0,
                        "steps": [{"name": "Execution Error", "status": "failed", "error": str(exc)}]
                    })
    else:
        # Sequential Execution
        for t in tasks:
            runner = VisiFlowYAMLRunner(t["file_path"])
            res = runner.execute(
                headless=t["headless"],
                report_path=t["report_path"],
                browser_type=browser_type,
                auto_heal=auto_heal,
                interactive=interactive
            )
            suite_results.append(res)

    total_suite_dur = time.time() - start_suite_time

    # Generate JUnit XML if requested
    if junit_path:
        generate_junit_xml(suite_results, junit_path)
        print(f"[*] Standard JUnit XML report generated: {junit_path}")

    # Summary Table
    passed_suites = sum(1 for s in suite_results if s["success"])
    total_suites = len(suite_results)
    all_pass = (passed_suites == total_suites)

    print("\n" + "=" * 60)
    print("[*] VisiFlow Test Suite Execution Summary")
    print("=" * 60)
    for s in suite_results:
        status_tag = "[PASS]" if s["success"] else "[FAIL]"
        print(f"  {status_tag} {Path(s['file']).name} ({s.get('passed_steps', 0)}/{s.get('total_steps', 0)} steps, {s.get('duration', 0.0):.1f}s)")
    print("-" * 60)
    print(f"Suites: {passed_suites}/{total_suites} passed | Total Time: {total_suite_dur:.1f}s")
    print("=" * 60 + "\n")

    return all_pass
