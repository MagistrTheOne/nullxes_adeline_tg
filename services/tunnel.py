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
_url_event: asyncio.Event | None = None


def get_public_url(fallback: str = "") -> str:
    return (_public_url or fallback or "").rstrip("/")


def set_public_url(url: str) -> bool:
    """Set runtime URL. Returns True if value changed."""
    global _public_url
    url = (url or "").strip().rstrip("/")
    if not url:
        return False
    changed = url != _public_url
    _public_url = url
    if changed:
        _write_env_webapp_url(url)
        logger.info("WEBAPP_PUBLIC_URL -> %s", url)
        if _url_event is not None:
            _url_event.set()
    return changed


def clear_runtime_url() -> None:
    """Forget stale runtime URL (keep .env as last-known hint only)."""
    global _public_url
    _public_url = ""
    if _url_event is not None:
        _url_event.clear()


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


async def wait_for_public_url(timeout: float = 45.0) -> str:
    """Block until tunnel publishes a URL (or timeout → empty)."""
    global _url_event
    if _public_url:
        return _public_url
    if _url_event is None:
        _url_event = asyncio.Event()
    try:
        await asyncio.wait_for(_url_event.wait(), timeout=timeout)
    except asyncio.TimeoutError:
        return ""
    return _public_url


async def start_localhost_run_tunnel(
    port: int,
    on_url=None,
) -> None:
    """Keep SSH reverse tunnel alive; update public URL when issued.

    on_url: optional async callable(url: str) — called only when URL changes.
    """
    global _tunnel_proc, _url_event

    if not tunnel_enabled():
        logger.info("START_TUNNEL=0 — туннель не поднимаю")
        return

    ssh = shutil.which("ssh")
    if not ssh:
        logger.error("ssh не найден — поставь OpenSSH Client в Windows")
        return

    if _url_event is None:
        _url_event = asyncio.Event()
    clear_runtime_url()

    backoff = 3
    while True:
        try:
            logger.info("Поднимаю localhost.run туннель -> 127.0.0.1:%s", port)
            _tunnel_proc = await asyncio.create_subprocess_exec(
                ssh,
                "-o",
                "StrictHostKeyChecking=accept-new",
                "-o",
                "TCPKeepAlive=yes",
                "-o",
                "ServerAliveInterval=15",
                "-o",
                "ServerAliveCountMax=4",
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
                # Skip huge QR noise in logs
                if line.count("\x1b[") > 3 or "█" in line:
                    continue
                logger.info("[tunnel] %s", line)
                m = URL_RE.search(line)
                if m:
                    url = m.group(0)
                    changed = set_public_url(url)
                    backoff = 3
                    if changed and on_url is not None:
                        try:
                            await on_url(url)
                        except Exception as exc:
                            logger.warning("on_url callback failed: %s", exc)
            code = await _tunnel_proc.wait()
            logger.warning("localhost.run tunnel exited code=%s", code)
        except asyncio.CancelledError:
            await stop_tunnel()
            raise
        except Exception as exc:
            logger.warning("tunnel error: %s", exc)

        clear_runtime_url()
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
