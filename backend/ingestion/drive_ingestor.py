import io
from typing import Iterator

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

GOOGLE_DOC_EXPORT_MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
GOOGLE_SLIDES_EXPORT_MIME = "application/vnd.openxmlformats-officedocument.presentationml.presentation"

SUPPORTED_BINARY_MIMES = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}
GOOGLE_NATIVE_MIMES = {
    "application/vnd.google-apps.document": ("docx", GOOGLE_DOC_EXPORT_MIME),
    "application/vnd.google-apps.presentation": ("pptx", GOOGLE_SLIDES_EXPORT_MIME),
}


def _build_credentials(access_token: str) -> Credentials:
    return Credentials(token=access_token)


def list_folder(access_token: str, folder_id: str, recursive: bool = True, max_depth: int = 5) -> Iterator[dict]:
    creds = _build_credentials(access_token)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)

    def _walk(current_folder_id: str, depth: int) -> Iterator[dict]:
        if depth > max_depth:
            return
        query = f"'{current_folder_id}' in parents and trashed = false"
        page_token = None
        while True:
            response = (
                service.files()
                .list(
                    q=query,
                    fields="nextPageToken, files(id, name, mimeType, modifiedTime)",
                    pageToken=page_token,
                    pageSize=100,
                    supportsAllDrives=True,
                    includeItemsFromAllDrives=True,
                )
                .execute()
            )
            for f in response.get("files", []):
                if f["mimeType"] == "application/vnd.google-apps.folder":
                    if recursive:
                        yield from _walk(f["id"], depth + 1)
                    continue
                yield f
            page_token = response.get("nextPageToken")
            if not page_token:
                break

    yield from _walk(folder_id, 0)


def download_file(access_token: str, file_meta: dict) -> tuple[bytes, str] | None:
    """
    Returns (bytes, ext) or None if file type is unsupported.
    `ext` is one of "pdf", "pptx", "docx".
    """
    creds = _build_credentials(access_token)
    service = build("drive", "v3", credentials=creds, cache_discovery=False)
    mime = file_meta["mimeType"]

    if mime in SUPPORTED_BINARY_MIMES:
        ext = SUPPORTED_BINARY_MIMES[mime]
        request = service.files().get_media(fileId=file_meta["id"])
    elif mime in GOOGLE_NATIVE_MIMES:
        ext, export_mime = GOOGLE_NATIVE_MIMES[mime]
        request = service.files().export_media(fileId=file_meta["id"], mimeType=export_mime)
    else:
        return None

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue(), ext
