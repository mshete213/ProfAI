import os
import threading
from pathlib import Path
from typing import Any, Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer
from watchdog.observers.api import BaseObserver

_observers: dict[str, BaseObserver] = {}
_lock = threading.Lock()


class _IngestHandler(FileSystemEventHandler):
    def __init__(self, course_id: str, extensions: set[str], callback: Callable[[str, str], None]):
        self.course_id = course_id
        self.extensions = extensions
        self.callback = callback

    def on_created(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        path = Path(os.fsdecode(event.src_path))
        if path.suffix.lower() in self.extensions:
            self.callback(self.course_id, str(path))


def start_watcher(
    path: str,
    course_id: str,
    file_extensions: list[str],
    on_new_file: Callable[[str, str], None],
) -> dict[str, Any]:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    key = f"{course_id}::{p.resolve()}"

    with _lock:
        if key in _observers:
            return {"status": "already_watching", "key": key}

        handler = _IngestHandler(course_id, {ext.lower() for ext in file_extensions}, on_new_file)
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
