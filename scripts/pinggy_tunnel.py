"""
Pinggy SSH tunnel extension for AUTOMATIC1111 WebUI
"""
import os
import re
import time
import logging
import subprocess
from pathlib import Path
from modules import shared, script_callbacks, scripts
import gradio as gr

# ------------------------------------------------------------------
# 0.  Paths & logging (reuse the original .cache folder)
# ------------------------------------------------------------------
CACHE_DIR = Path(shared.script_path) / "extensions" / "sd-webui-pinggy" / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=CACHE_DIR / "pinggy.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# ------------------------------------------------------------------
# 1.  Small helpers (copied from tunnel_v4.py, trimmed)
# ------------------------------------------------------------------
ANSI = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
CTRL  = re.compile(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]')

def _clean(raw: str) -> str:
    return CTRL.sub('', ANSI.sub('', raw))

def _find_urls(text: str):
    patterns = [
        r'https?://[a-zA-Z0-9-]+\.a\.free\.pinggy\.link',
        r'https?://[a-zA-Z0-9-]+\.a\.pinggy\.link',
        r'https?://[a-zA-Z0-9-]+\.pinggy\.link',
    ]
    hits = []
    for p in patterns:
        hits.extend(re.findall(p, text))
    return list(dict.fromkeys(hits))   # unique in order

# ------------------------------------------------------------------
# 2.  Start tunnel in a background thread
# ------------------------------------------------------------------
_tunnel_proc = None        # global to avoid duplicate processes

def _start_tunnel():
    """Launch SSH reverse tunnel to Pinggy on whatever port WebUI is running."""
    global _tunnel_proc
    if _tunnel_proc and _tunnel_proc.poll() is None:
        logging.info("Tunnel already running")
        return

    port = shared.cmd_opts.port if shared.cmd_opts.port else 7860
    output_file = CACHE_DIR / "url.txt"
    cmd = (
        f'ssh -o StrictHostKeyChecking=no -p 80 '
        f'-R0:localhost:{port} auth@a.pinggy.io > {output_file}'
    )

    logging.info(f"Starting tunnel on port {port}")
    _tunnel_proc = subprocess.Popen(cmd, shell=True)

# ------------------------------------------------------------------
# 3.  Poll .cache/url.txt and print any discovered URL(s)
# ------------------------------------------------------------------
def _monitor():
    output_file = CACHE_DIR / "url.txt"
    while True:
        time.sleep(2)
        try:
            txt = _clean(open(output_file).read())
            for url in _find_urls(txt):
                print(f"\n🚀  Pinggy tunnel ready: {url}\n")
                # Once we have at least one URL we can slow polling down
                time.sleep(30)
        except Exception:
            pass

# ------------------------------------------------------------------
# 4.  Hook into WebUI
# ------------------------------------------------------------------
class PinggyScript(scripts.Script):
    def title(self):
        return "Pinggy tunnel"

    def show(self, is_img2img):
        return scripts.AlwaysVisible

    def ui(self, is_img2img):
        # Add a small “Start tunnel” button (purely cosmetic; auto-starts anyway)
        with gr.Group():
            with gr.Row():
                btn = gr.Button("Start / restart Pinggy tunnel", variant="primary")
                btn.click(fn=_start_tunnel, inputs=[], outputs=[])
        return []

def _init():
    _start_tunnel()
    import threading
    threading.Thread(target=_monitor, daemon=True).start()

# Register the callback as soon as the script is imported
script_callbacks.on_app_started(lambda _: _init())
