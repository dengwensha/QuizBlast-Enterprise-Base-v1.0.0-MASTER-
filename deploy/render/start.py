"""Render-only launcher for the single frontend/backend container."""
import os
import pathlib
import signal
import subprocess
import sys
import time

SOURCE = pathlib.Path("/etc/nginx/quizblast.conf.template")
TARGET = pathlib.Path("/etc/nginx/conf.d/quizblast.conf")


def configure():
    port = os.environ.get("PORT", "10000")
    if not port.isascii() or not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise ValueError("PORT must be a valid TCP port")
    source = SOURCE.read_text(encoding="utf-8")
    if source.count("listen 80;") != 1:
        raise RuntimeError("Unexpected Nginx listen configuration")
    if source.count("backend:8000") != 2:
        raise RuntimeError("Unexpected Nginx backend routing")
    config = source.replace("listen 80;", f"listen {int(port)};")
    config = config.replace("backend:8000", "127.0.0.1:8000")
    TARGET.write_text(config, encoding="utf-8")
    subprocess.run(["nginx", "-t"], check=True)


def main():
    configure()
    if sys.argv[1:] == ["--check"]:
        print("Render Nginx configuration PASS")
        return
    if not os.getenv("DATABASE_URL") or not os.getenv("SECRET_KEY"):
        raise RuntimeError("DATABASE_URL and SECRET_KEY are required")

    children = []
    shutting_down = False

    def stop(_signal, _frame):
        nonlocal shutting_down
        shutting_down = True
        for child in children:
            if child.poll() is None:
                child.terminate()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)

    try:
        children.append(subprocess.Popen([
            "uvicorn", "app.main:app", "--host", "127.0.0.1",
            "--port", "8000", "--workers", "1",
        ]))
        children.append(subprocess.Popen(["nginx", "-g", "daemon off;"]))
        while not shutting_down and all(p.poll() is None for p in children):
            time.sleep(0.5)
    finally:
        for child in children:
            if child.poll() is None:
                child.terminate()
        for child in children:
            try:
                child.wait(timeout=8)
            except subprocess.TimeoutExpired:
                child.kill()
                child.wait()
    if not shutting_down:
        raise RuntimeError("Render application process exited unexpectedly")


if __name__ == "__main__":
    main()
