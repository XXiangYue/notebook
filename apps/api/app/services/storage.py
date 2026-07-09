import hashlib
import uuid
from dataclasses import dataclass
from pathlib import Path

from fastapi import UploadFile

from apps.api.app.config import Settings


class AttachmentValidationError(Exception):
    pass


@dataclass(frozen=True)
class StoredFile:
    storage_key: str
    original_filename: str
    media_type: str
    size_bytes: int
    sha256: str


class LocalAttachmentStorage:
    def __init__(self, settings: Settings):
        self.root = Path(settings.storage_root).resolve() / "attachments"
        self.max_bytes = settings.max_attachment_bytes
        self.allowed_types = settings.allowed_attachment_type_set

    async def save(self, block_id: uuid.UUID, upload: UploadFile) -> StoredFile:
        media_type = upload.content_type or "application/octet-stream"
        if media_type not in self.allowed_types:
            raise AttachmentValidationError("Unsupported attachment type")

        original_filename = Path(upload.filename or "attachment").name
        suffix = Path(original_filename).suffix.lower()
        storage_key = f"{block_id}/{uuid.uuid4().hex}{suffix}"
        destination = self.root / storage_key
        destination.parent.mkdir(parents=True, exist_ok=True)

        digest = hashlib.sha256()
        size = 0
        try:
            with destination.open("xb") as output:
                while chunk := await upload.read(1024 * 1024):
                    size += len(chunk)
                    if size > self.max_bytes:
                        raise AttachmentValidationError("Attachment exceeds size limit")
                    digest.update(chunk)
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        finally:
            await upload.close()

        if size == 0:
            destination.unlink(missing_ok=True)
            raise AttachmentValidationError("Attachment must not be empty")

        return StoredFile(
            storage_key=storage_key,
            original_filename=original_filename,
            media_type=media_type,
            size_bytes=size,
            sha256=digest.hexdigest(),
        )

    def path_for(self, storage_key: str) -> Path:
        path = (self.root / storage_key).resolve()
        if not path.is_relative_to(self.root):
            raise AttachmentValidationError("Invalid storage key")
        return path

    def delete(self, storage_key: str) -> None:
        self.path_for(storage_key).unlink(missing_ok=True)
