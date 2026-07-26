"""Auto localhost.run tunnel for Mini App HTTPS URL."""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = ROOT / ".env"
URL_RE = re.compile(r"https://[a-zA-Z0-9-]+\.lhr\.life")

_public_url: str = ""
_tunnel_proc: asyncio.subprocess.Process | None = None


def get_public_url(fallback: str = "") -> str:
    return (_public_url or fallback or "").rstrip("/")


def set_public_url(url: str) -> None:
    global _public_url
    url = (url or "").strip().rstrip("/")
    if not url:
        return
    _public_url = url
    _write_env_webapp_url(url)
    logger.info("WEBAPP_PUBLIC_URL -> %s", url)


def _write_env_webapp_url(url: str) -> None:
    try:
        if ENV_PATH.exists():
            lines = ENV_PATH.read_text(encoding="utf-8").splitlines()
        else:
            lines = []
        key = "WEBAPP_PUBLIC_URL="
        out: list[str] = []
        found = False
        for line in lines:
            if line.startswith(key) or line.startswith("WEBAPP_PUBLIC_URL ="):
                out.append(f"WEBAPP_PUBLIC_URL={url}")
                found = True
            else:
                out.append(line)
        if not found:
            out.append(f"WEBAPP_PUBLIC_URL={url}")
        ENV_PATH.write_text("\n".join(out) + "\n", encoding="utf-8")
    except Exception as exc:
        logger.warning("Failed to write WEBAPP_PUBLIC_URL to .env: %s", exc)


def tunnel_enabled() -> bool:
    raw = os.getenv("START_TUNNEL", "1").strip().lower()
    return raw in {"1", "true", "yes", "on"}


async def start_localhost_run_tunnel(port: int) -> None:
    """Keep SSH reverse tunnel alive; update public URL when issued."""
    global _tunnel_proc

    if not tunnel_enabled():
        logger.info("START_TUNNEL=0 — туннель не поднимаю")
        return

    ssh = shutil.which("ssh")
    if not ssh:
        logger.error("ssh не найден — поставь OpenSSH Client в Windows")
        return

    backoff = 3
    while True:
        try:
            logger.info("Поднимаю localhost.run туннель -> 127.0.0.1:%s", port)
            _tunnel_proc = await asyncio.create_subprocess_exec(
                ssh,
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "ServerAliveInterval=30",
                "-o",
                "ServerAliveCountMax=3",
                "-o",
                "ExitOnForwardFailure=yes",
                "-R",
                f"80:127.0.0.1:{port}",
                "nokey@localhost.run",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            assert _tunnel_proc.stdout is not None
            while True:
                line_b = await _tunnel_proc.stdout.readline()
                if not line_b:
                    break
                line = line_b.decode("utf-8", errors="replace").strip()
                if not line:
                    continue
                logger.info("[tunnel] %s", line)
                m = URL_RE.search(line)
                if m:
                    set_public_url(m.group(0))
                    backoff = 3
            code = await _tunnel_proc.wait()
            logger.warning("localhost.run tunnel exited code=%s", code)
        except asyncio.CancelledError:
            await stop_tunnel()
            raise
        except Exception as exc:
            logger.warning("tunnel error: %s", exc)

        logger.info("Переподключение туннеля через %ss…", backoff)
        await asyncio.sleep(backoff)
        backoff = min(backoff * 2, 60)


async def stop_tunnel() -> None:
    global _tunnel_proc
    proc = _tunnel_proc
    _tunnel_proc = None
    if proc and proc.returncode is None:
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5)
            except asyncio.TimeoutError:
                proc.kill()
        except Exception:
            pass
