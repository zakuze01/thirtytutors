"""Windows frozen entry; smoke mode never requires a Gemini key or microphone."""

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path


def main():
    started = time.perf_counter()
    parser = argparse.ArgumentParser(description="Companion Lite desktop")
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1"])
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument("--smoke-output", type=Path)
    args = parser.parse_args()
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w")
    from thirtytutors import desktop

    if args.smoke_test:
        if not args.smoke_output or not args.smoke_output.is_absolute():
            parser.error("--smoke-test requires absolute --smoke-output")
        original = desktop.webview.create_window
        result = {"loaded": False}

        def create(*a, **kw):
            window = original(*a, **kw)

            def loaded():
                result.update(loaded=True, loaded_seconds=round(time.perf_counter() - started, 3))
                try:
                    result["ui"] = window.evaluate_js(
                        "({title:document.title,mic:document.getElementById('micStatus')?.textContent})"
                    )
                except Exception:
                    result["inspection"] = "unavailable"

            window.events.loaded += loaded

            def close():
                try:
                    result["ui"] = window.evaluate_js(
                        "({title:document.title,mic:document.getElementById('micStatus')?.textContent})"
                    )
                except Exception:
                    pass
                args.smoke_output.write_text(json.dumps(result, indent=2), encoding="utf-8")
                window.destroy()

            timer = threading.Timer(12, close)
            timer.daemon = True
            timer.start()
            return window

        desktop.webview.create_window = create
    desktop.run(host=args.host, port=args.port)


if __name__ == "__main__":
    main()
