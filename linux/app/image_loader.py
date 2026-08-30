"""linux/app/image_loader.py — Async poster image loader with Smart LRU disk cache."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable

import httpx
import gi

gi.require_version("Gdk", "4.0")
from gi.repository import Gdk, GLib


logger = logging.getLogger(__name__)

CACHE_DIR = Path.home() / ".cache" / "reclens" / "posters"
MAX_CACHE_BYTES = 500 * 1024 * 1024  # 500 MB
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w500"
TMDB_BACKDROP_BASE = "https://image.tmdb.org/t/p/w1280"


class ImageLoader:
    """Thread-safe, non-blocking image loader with local disk LRU cache."""

    def __init__(self, cache_dir: Path = CACHE_DIR, max_workers: int = 6) -> None:
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="ImageLoader")
        self._memory_cache: dict[str, Gdk.Texture] = {}
        self._lock = threading.Lock()
        self._prune_cache_if_needed()

    def get_texture_async(
        self,
        url_or_path: str,
        callback: Callable[[Gdk.Texture | None], None],
        is_backdrop: bool = False,
    ) -> None:
        """Asynchronously load a texture and invoke callback on the GTK main thread."""
        if not url_or_path or url_or_path == "nan":
            callback(None)
            return

        # Resolve full URL
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            full_url = url_or_path
        else:
            base = TMDB_BACKDROP_BASE if is_backdrop else TMDB_IMAGE_BASE
            full_url = f"{base}/{url_or_path.lstrip('/')}"

        # Check memory cache
        with self._lock:
            if full_url in self._memory_cache:
                callback(self._memory_cache[full_url])
                return

        # Check disk cache
        cache_key = hashlib.sha256(full_url.encode("utf-8")).hexdigest() + ".jpg"
        disk_path = self.cache_dir / cache_key

        if disk_path.exists():
            # Update atime
            try:
                os.utime(disk_path, None)
                texture = Gdk.Texture.new_from_filename(str(disk_path))
                with self._lock:
                    self._memory_cache[full_url] = texture
                callback(texture)
                return
            except Exception as e:
                logger.warning("Failed to load cached texture %s: %s", disk_path, e)

        # Download in background worker thread
        def _worker():
            texture = None
            try:
                with httpx.Client(timeout=8.0, follow_redirects=True) as client:
                    resp = client.get(full_url)
                    if resp.status_code == 200 and resp.content:
                        with open(disk_path, "wb") as f:
                            f.write(resp.content)
                        texture = Gdk.Texture.new_from_filename(str(disk_path))
                        with self._lock:
                            self._memory_cache[full_url] = texture
            except Exception as e:
                logger.debug("Failed to download image %s: %s", full_url, e)

            # Schedule callback on GTK Main Thread
            GLib.idle_add(callback, texture)

        self.executor.submit(_worker)

    def get_cached_path(self, url_or_path: str, is_backdrop: bool = False) -> Path | None:
        """Return the on-disk cached Path if the image is downloaded."""
        if not url_or_path or url_or_path == "nan":
            return None
        if url_or_path.startswith("http://") or url_or_path.startswith("https://"):
            full_url = url_or_path
        else:
            base = TMDB_BACKDROP_BASE if is_backdrop else TMDB_IMAGE_BASE
            full_url = f"{base}/{url_or_path.lstrip('/')}"
        cache_key = hashlib.sha256(full_url.encode("utf-8")).hexdigest() + ".jpg"
        disk_path = self.cache_dir / cache_key
        return disk_path if disk_path.exists() else None


    def _prune_cache_if_needed(self) -> None:
        """Prune oldest files if cache exceeds MAX_CACHE_BYTES."""
        try:
            files = list(self.cache_dir.glob("*.jpg"))
            total_size = sum(f.stat().st_size for f in files)
            if total_size <= MAX_CACHE_BYTES:
                return

            # Sort by access time ascending
            files.sort(key=lambda f: f.stat().st_atime)
            bytes_to_delete = total_size - int(MAX_CACHE_BYTES * 0.8)
            deleted = 0
            for f in files:
                if deleted >= bytes_to_delete:
                    break
                sz = f.stat().st_size
                f.unlink(missing_ok=True)
                deleted += sz
        except Exception as e:
            logger.warning("Error pruning image cache: %s", e)

    def clear_cache(self) -> None:
        """Clear all cached images."""
        with self._lock:
            self._memory_cache.clear()
        shutil.rmtree(self.cache_dir, ignore_errors=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)


# Global singleton instance
image_loader = ImageLoader()
