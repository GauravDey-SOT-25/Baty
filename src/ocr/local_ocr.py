"""Local OCR using macOS Vision; images and extracted text remain on this Mac."""
from __future__ import annotations

import base64
import binascii
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SWIFT_SOURCE = ROOT / "src" / "ocr" / "vision_ocr.swift"
_MAX_IMAGE_BYTES = 4 * 1024 * 1024
_MAX_TEXT_CHARS = 24_000
_BUILD_LOCK = threading.Lock()


class OCRUnavailableError(RuntimeError):
    """The local Apple Vision OCR runtime could not be started."""


def _binary_path() -> Path:
    swiftc = shutil.which("swiftc")
    if not swiftc:
        raise OCRUnavailableError("Local OCR requires the macOS Swift compiler (swiftc).")
    build_dir = ROOT / "work" / "local-ocr"
    build_dir.mkdir(parents=True, exist_ok=True)
    binary = build_dir / "vision-ocr"
    try:
        stale = not binary.is_file() or binary.stat().st_mtime < SWIFT_SOURCE.stat().st_mtime
    except OSError as exc:
        raise OCRUnavailableError("The local OCR helper is unavailable.") from exc
    if stale:
        with _BUILD_LOCK:
            stale = not binary.is_file() or binary.stat().st_mtime < SWIFT_SOURCE.stat().st_mtime
            if stale:
                try:
                    built = subprocess.run(
                        [swiftc, "-O", "-framework", "Vision", "-framework", "ImageIO", str(SWIFT_SOURCE), "-o", str(binary)],
                        capture_output=True, text=True, timeout=90, check=False,
                    )
                except (OSError, subprocess.TimeoutExpired) as exc:
                    raise OCRUnavailableError("Could not build the local macOS OCR helper.") from exc
                if built.returncode:
                    raise OCRUnavailableError("Could not build the local macOS OCR helper.")
                try:
                    os.chmod(binary, 0o700)
                except OSError:
                    pass
    return binary


def extract_text_from_base64(encoded: str) -> str:
    """Decode a bounded image and extract text without network access."""
    try:
        raw = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("Image data must be valid base64.") from exc
    if not raw or len(raw) > _MAX_IMAGE_BYTES:
        raise ValueError("Choose an image smaller than 4 MiB.")
    # Accept common raster formats only; ImageIO performs the actual decode.
    is_png = raw.startswith(b"\x89PNG\r\n\x1a\n")
    is_jpeg = raw.startswith(b"\xff\xd8\xff")
    is_gif = raw.startswith((b"GIF87a", b"GIF89a"))
    is_webp = len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    is_heif = len(raw) >= 12 and raw[4:8] == b"ftyp" and raw[8:12] in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}
    if not (is_png or is_jpeg or is_gif or is_webp or is_heif):
        raise ValueError("Use a PNG, JPEG, GIF, WebP, or HEIC image.")
    binary = _binary_path()
    with tempfile.NamedTemporaryFile(prefix="local-ocr-", suffix=".image", delete=False) as handle:
        image_path = Path(handle.name)
        try:
            os.chmod(image_path, 0o600)
        except OSError:
            pass
        handle.write(raw)
    try:
        try:
            result = subprocess.run([str(binary), str(image_path)], capture_output=True, timeout=45, check=False)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise OCRUnavailableError("Local OCR timed out or could not start.") from exc
        if result.returncode:
            message = result.stderr.decode("utf-8", "replace").strip()[:300]
            raise ValueError(message or "The selected image could not be read.")
        text = result.stdout.decode("utf-8", "replace").strip()
        if len(text) > _MAX_TEXT_CHARS:
            text = text[:_MAX_TEXT_CHARS]
        return text
    finally:
        image_path.unlink(missing_ok=True)
