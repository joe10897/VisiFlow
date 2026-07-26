import os
import time
import base64
from typing import List, Dict, Any

class VisiFlowReporter:
    def __init__(self):
        self.steps = []
        self.start_time = time.time()

    def start_step(self, action: str, target: str, screenshot_path: str):
        """
        Record the start of a test step.
        """
        img_base64 = ""
        if screenshot_path and os.path.exists(screenshot_path):
            try:
                with open(screenshot_path, "rb") as f:
                    img_base64 = base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass

        step = {
            "action": action,
            "target": target,
            "screenshot_before": img_base64,
            "screenshot_after": "",
            "status": "Running",
            "score": 1.0,
            "healed": False,
            "original_match": "",
            "healed_match": "",
            "timestamp": time.strftime("%H:%M:%S"),
            "duration": 0.0,
            "start_t": time.time()
        }
        self.steps.append(step)
        return len(self.steps) - 1

    def end_step(self, step_idx: int, success: bool, score: float, healed: bool, original_match: str, healed_match: str, screenshot_path_after: str = None):
        """
        Record the completion of a test step.
        """
        if step_idx < 0 or step_idx >= len(self.steps):
            return

        step = self.steps[step_idx]
        step["duration"] = round(time.time() - step["start_t"], 2)
        step["status"] = "Success" if success else "Failed"
        step["score"] = round(score, 2)
        step["healed"] = healed
        step["original_match"] = original_match
        step["healed_match"] = healed_match
        
        if healed and success:
            step["status"] = "Healed"

        if screenshot_path_after and os.path.exists(screenshot_path_after):
            try:
                with open(screenshot_path_after, "rb") as f:
                    step["screenshot_after"] = base64.b64encode(f.read()).decode("utf-8")
            except Exception:
                pass

    def generate_html_report(self, output_path: str = "visiflow_report.html"):
        """
        Generate a self-contained, interactive glassmorphic HTML report.
        """
        total_steps = len(self.steps)
        healed_count = sum(1 for s in self.steps if s["healed"])
        success_count = sum(1 for s in self.steps if s["status"] in ("Success", "Healed"))
        failed_count = total_steps - success_count
        duration = round(time.time() - self.start_time, 2)

        steps_html = ""
        for i, s in enumerate(self.steps):
            status_color = "text-emerald-400 border-emerald-500/30 bg-emerald-500/10"
            if s["status"] == "Failed":
                status_color = "text-rose-400 border-rose-500/30 bg-rose-500/10"
            elif s["status"] == "Healed":
                status_color = "text-amber-400 border-amber-500/30 bg-amber-500/10"

            healed_log = ""
            if s["healed"]:
                healed_log = f"""
                <div class="mt-4 p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300">
                    <strong>Self-Healing Log:</strong> Target query '{s["target"]}' matched text '{s["healed_match"]}' (Fuzzy similarity: {s["score"]})
                </div>
                """

            img_before_html = ""
            if s["screenshot_before"]:
                img_before_html = f"""
                <div>
                    <span class="text-[10px] text-gray-500 block mb-1">Before Action</span>
                    <img src="data:image/png;base64,{s["screenshot_before"]}" class="w-full rounded border border-white/5 shadow-md max-h-[300px] object-contain bg-slate-950" />
                </div>
                """

            img_after_html = ""
            if s["screenshot_after"]:
                img_after_html = f"""
                <div>
                    <span class="text-[10px] text-gray-500 block mb-1">After Action</span>
                    <img src="data:image/png;base64,{s["screenshot_after"]}" class="w-full rounded border border-white/5 shadow-md max-h-[300px] object-contain bg-slate-950" />
                </div>
                """

            steps_html += f"""
            <!-- Step {i+1} -->
            <div class="border border-white/5 bg-white/[0.02] backdrop-blur-md rounded-xl p-6 transition-all hover:bg-white/[0.04]">
                <div class="flex flex-wrap justify-between items-center gap-4 mb-4">
                    <div class="flex items-center gap-3">
                        <span class="w-8 h-8 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center font-bold text-sm">
                            {i+1}
                        </span>
                        <div>
                            <h4 class="font-semibold text-white">{s["action"]} '{s["target"]}'</h4>
                            <p class="text-xs text-gray-400">Duration: {s["duration"]}s | Time: {s["timestamp"]}</p>
                        </div>
                    </div>
                    <span class="text-xs px-3 py-1 border rounded-full font-semibold uppercase tracking-wider {status_color}">
                        {s["status"]}
                    </span>
                </div>

                {healed_log}

                <div class="grid grid-cols-1 md:grid-cols-2 gap-6 mt-4">
                    {img_before_html}
                    {img_after_html}
                </div>
            </div>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VisiFlow Automation Report</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&family=JetBrains+Mono&display=swap" rel="stylesheet">
    <style>
        body {{
            font-family: 'Outfit', sans-serif;
            background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
            min-height: 100vh;
        }}
    </style>
</head>
<body class="text-slate-200 py-12 px-6">
    <div class="max-w-5xl mx-auto">
        <!-- Header -->
        <header class="flex justify-between items-center mb-12 border-b border-white/10 pb-6">
            <div>
                <h1 class="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
                    👁️ VisiFlow <span class="text-blue-400">Report</span>
                </h1>
                <p class="text-sm text-gray-400 mt-1">Automated E2E Visual Execution & Self-Healing Summary</p>
            </div>
            <div class="text-right">
                <span class="text-xs font-mono text-gray-500 uppercase tracking-widest block">Total Duration</span>
                <span class="text-xl font-bold text-white">{duration}s</span>
            </div>
        </header>

        <!-- Dashboard Metrics -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-6 mb-12">
            <div class="bg-white/[0.02] border border-white/5 rounded-xl p-5 backdrop-blur-md">
                <span class="text-xs text-gray-500 uppercase tracking-wider block">Total Steps</span>
                <span class="text-3xl font-bold text-white mt-1 block">{total_steps}</span>
            </div>
            <div class="bg-white/[0.02] border border-white/5 rounded-xl p-5 backdrop-blur-md">
                <span class="text-xs text-gray-500 uppercase tracking-wider block">Succeeded</span>
                <span class="text-3xl font-bold text-emerald-400 mt-1 block">{success_count}</span>
            </div>
            <div class="bg-white/[0.02] border border-white/5 rounded-xl p-5 backdrop-blur-md">
                <span class="text-xs text-gray-500 uppercase tracking-wider block">Self-Healed</span>
                <span class="text-3xl font-bold text-amber-400 mt-1 block">{healed_count}</span>
            </div>
            <div class="bg-white/[0.02] border border-white/5 rounded-xl p-5 backdrop-blur-md">
                <span class="text-xs text-gray-500 uppercase tracking-wider block">Failed</span>
                <span class="text-3xl font-bold text-rose-400 mt-1 block">{failed_count}</span>
            </div>
        </div>

        <!-- Step List -->
        <div class="space-y-6">
            <h3 class="text-xl font-bold text-white mb-4">Execution Step Timeline</h3>
            {steps_html if steps_html else '<p class="text-gray-500 text-center py-8">No steps executed yet.</p>'}
        </div>
    </div>
</body>
</html>
"""
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path

# Global singleton reporter instance
global_reporter = VisiFlowReporter()
