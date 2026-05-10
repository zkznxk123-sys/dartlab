from __future__ import annotations

import base64
import io
import subprocess
import threading
from typing import Any

from dartlab.channel import DevTunnelSetupError, setupDevtunnel


class DevChannelRuntime:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._url: str | None = None
        self._process: subprocess.Popen | None = None
        self._error: str | None = None

    def status(self) -> dict[str, Any]:
        with self._lock:
            running = self._process is not None and self._process.poll() is None
            if not running:
                self._process = None
            url = self._url if running else None
            return self._buildStatus(url=url, running=running, error=self._error)

    def start(self, *, port: int, autoYes: bool = True) -> dict[str, Any]:
        with self._lock:
            if self._process is not None and self._process.poll() is None and self._url:
                return self._buildStatus(url=self._url, running=True, error=None)
            self._error = None

        try:
            url, process = setupDevtunnel(port=port, autoYes=autoYes)
        except DevTunnelSetupError as exc:
            with self._lock:
                self._error = str(exc)
            return self._buildStatus(url=None, running=False, error=str(exc))

        with self._lock:
            self._url = url
            self._process = process
            self._error = None
            return self._buildStatus(url=url, running=True, error=None)

    def stop(self) -> dict[str, Any]:
        with self._lock:
            process = self._process
            self._process = None
            self._url = None
            self._error = None
        if process is not None and process.poll() is None:
            process.terminate()
        return self._buildStatus(url=None, running=False, error=None)

    def shutdown(self) -> None:
        self.stop()

    def _buildStatus(self, *, url: str | None, running: bool, error: str | None) -> dict[str, Any]:
        qr_data_url = _qrDataUrl(url) if url else None
        return {
            "kind": "devtunnel",
            "label": "Dev Channel",
            "running": running,
            "url": url,
            "qrDataUrl": qr_data_url,
            "error": error,
        }


def _qrDataUrl(url: str | None) -> str | None:
    if not url:
        return None
    try:
        import qrcode
        from qrcode.image.svg import SvgPathImage

        qr = qrcode.QRCode(border=2, error_correction=qrcode.constants.ERROR_CORRECT_M)
        qr.add_data(url)
        qr.make(fit=True)
        img = qr.make_image(image_factory=SvgPathImage)
        buf = io.BytesIO()
        img.save(buf)
        encoded = base64.b64encode(buf.getvalue()).decode("ascii")
        return f"data:image/svg+xml;base64,{encoded}"
    except Exception:
        return None


dev_channel_runtime = DevChannelRuntime()
