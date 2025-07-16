import os
import re
import time
import logging
import subprocess
from pathlib import Path
from modules import shared, script_callbacks, scripts
import gradio as gr

CACHE_DIR = Path(shared.script_path) / "extensions" / "pgn" / ".cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

logging.basicConfig(
    filename=CACHE_DIR / "pinggy.log",
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

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
        f'sshpass -p 0000 ssh -o StrictHostKeyChecking=no -p 80 '
        f'-R0:localhost:{port} auth@a.pinggy.io > {output_file}'
    )

    logging.info(f"Starting tunnel on port {port}")
    _tunnel_proc = subprocess.Popen(cmd, shell=True)

_shown_once = False

def _monitor():
    output_file = CACHE_DIR / "url.txt"
    while True:
        time.sleep(2)
        try:
            txt = _clean(open(output_file).read())
            for url in _find_urls(txt):
                global _shown_once
                if not _shown_once:               # only print once
                    print(f"\nPinggy tunnel ready: {url}\n")
                    _shown_once = True
        except Exception:
            pass

class PinggyScript(scripts.Script):
    def title(self):
        return "Pinggy tunnel"

    def show(self, is_img2img):
        return False
        
def _init():
    _start_tunnel()
    import threading
    threading.Thread(target=_monitor, daemon=True).start()

# Register the callback as soon as the script is imported
def _on_app_started(demo, app):
    _init()

script_callbacks.on_app_started(_on_app_started)
