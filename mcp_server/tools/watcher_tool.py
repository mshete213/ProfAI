"""
Folder watcher tool for the MCP server.

Maintains a per-process registry of watchdog Observers. When a new file
appears in a watched directory, it is POSTed to the backend's internal
upload endpoint.
"""
import os
import threading
from pathlib import Path
from typing import Any

import httpx
import structlog
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

logger = structlog.get_logger()

_observers: dict[str, BaseObserver] = {}
_lock = threading.Lock()


class _IngestHandler(FileSystemEventHandler):
    def __init__(self, course_id: str, extensions: set[str], backend_url: str, internal_key: str):
        self.course_id = course_id
        self.extensions = {e.lower() for e in extensions}
        self.backend_url = backend_url
        self.internal_key = internal_key

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(os.fsdecode(event.src_path))
        if path.suffix.lower() not in self.extensions:
            return
        try:
            with open(path, "rb") as f:
                files = {"files": (path.name, f, "application/octet-stream")}
                r = httpx.post(
                    f"{self.backend_url}/api/v1/internal/ingest/{self.course_id}/upload",
                    files=files,
                    headers={"X-Internal-Key": self.internal_key},
                    timeout=120.0,
                )
            logger.info(
                "watcher.posted",
                file=path.name,
                status_code=r.status_code,
                course=self.course_id,
            )
        except Exception as exc:
            logger.exception("watcher.post_failed", file=path.name, error=str(exc))


def start_watcher(
    path: str,
    course_id: str,
    file_extensions: list[str],
    backend_url: str,
    internal_key: str,
) -> dict[str, Any]:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    key = f"{course_id}::{p.resolve()}"

    with _lock:
        if key in _observers:
            return {"status": "already_watching", "key": key, "path": str(p.resolve())}

        handler = _IngestHandler(course_id, set(file_extensions), backend_url, internal_key)
        observer = Observer()
        observer.schedule(handler, str(p), recursive=False)
        observer.daemon = True
        observer.start()
        _observers[key] = observer

    return {"status": "watching", "key": key, "path": str(p.resolve())}


def stop_watcher(course_id: str, path: str) -> dict[str, Any]:
    p = Path(path)
    key = f"{course_id}::{p.resolve()}"
    with _lock:
        observer = _observers.pop(key, None)
    if observer is None:
        return {"status": "not_watching", "key": key}
    observer.stop()
    observer.join(timeout=5)
    return {"status": "stopped", "key": key}


def list_watchers() -> list[str]:
    with _lock:
        return list(_observers.keys())
