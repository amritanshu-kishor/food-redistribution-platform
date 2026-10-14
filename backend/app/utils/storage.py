import os
import uuid
import shutil
import logging
from pathlib import Path
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

logger = logging.getLogger("foodshare.storage")

# Create upload directories locally if local storage is configured
if settings.STORAGE_PROVIDER == "local":
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "images"), exist_ok=True)
    os.makedirs(os.path.join(settings.UPLOAD_DIR, "documents"), exist_ok=True)

def validate_file(file: UploadFile, is_image: bool = False) -> int:
    """Validate file type and size."""
    # Measure file size
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)  # Reset pointer
    
    # 5MB limit for images, 10MB limit for verification documents
    max_size = 5 * 1024 * 1024 if is_image else 10 * 1024 * 1024
    if file_size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum allowed size is {max_mb}MB."
        )
        
    # Extensions and content types
    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()
    if is_image:
        allowed_exts = {".jpg", ".jpeg", ".png", ".webp"}
        allowed_types = {"image/jpeg", "image/png", "image/webp"}
    else:
        allowed_exts = {".pdf", ".doc", ".docx", ".jpg", ".jpeg", ".png"}
        allowed_types = {
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "image/jpeg",
            "image/png"
        }
        
    if ext not in allowed_exts or file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type {ext} not allowed."
        )

    # Content-Type and extension are client-controlled. Verify common magic
    # bytes too, and reject formats that could be served as active content.
    header = file.file.read(16)
    file.file.seek(0)
    signatures = {
        ".pdf": header.startswith(b"%PDF"),
        ".jpg": header.startswith(b"\xff\xd8\xff"),
        ".jpeg": header.startswith(b"\xff\xd8\xff"),
        ".png": header.startswith(b"\x89PNG\r\n\x1a\n"),
        ".webp": header.startswith(b"RIFF") and header[8:12] == b"WEBP",
        ".doc": header.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"),
        ".docx": header.startswith(b"PK\x03\x04"),
    }
    if not signatures.get(ext, False):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="File contents do not match the declared file type")
    return file_size

def save_uploaded_file(file: UploadFile, is_image: bool = False) -> str:
    """Save uploaded file to S3 or local directory, returning path/URL."""
    validate_file(file, is_image)
    
    filename = file.filename or "upload"
    unique_filename = f"{uuid.uuid4().hex}{os.path.splitext(filename)[1].lower()}"
    subfolder = "images" if is_image else "documents"
    
    if settings.STORAGE_PROVIDER == "local":
        base_dir = Path(settings.UPLOAD_DIR).resolve()
        file_path = (base_dir / subfolder / unique_filename).resolve()
        if base_dir not in file_path.parents:
            raise HTTPException(status_code=400, detail="Invalid upload path")
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return f"/uploads/{subfolder}/{unique_filename}"
    else:
        try:
            import boto3
        except ImportError:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AWS SDK boto3 not installed."
            )
        
        s3_client = boto3.client(
            "s3",
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        s3_key = f"{subfolder}/{unique_filename}"
        try:
            s3_client.upload_fileobj(
                file.file,
                settings.AWS_S3_BUCKET_NAME,
                s3_key,
                ExtraArgs={"ContentType": file.content_type}
            )
            return f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/{s3_key}"
        except Exception:
            logger.exception("S3 upload failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to upload file to storage"
            )

def delete_uploaded_file(file_path: str) -> bool:
    """Delete uploaded file from the storage backend."""
    if not file_path:
        return False
        
    if settings.STORAGE_PROVIDER == "local":
        if file_path.startswith("/uploads/"):
            relative_path = file_path.removeprefix("/uploads/")
            base_dir = Path(settings.UPLOAD_DIR).resolve()
            local_path = (base_dir / relative_path).resolve()
            if base_dir in local_path.parents and local_path.is_file():
                local_path.unlink()
                return True
    else:
        try:
            import boto3
        except ImportError:
            return False
        
        prefix = f"https://{settings.AWS_S3_BUCKET_NAME}.s3.{settings.AWS_REGION}.amazonaws.com/"
        if file_path.startswith(prefix):
            s3_key = file_path.replace(prefix, "")
            s3_client = boto3.client(
                "s3",
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
                region_name=settings.AWS_REGION
            )
            try:
                s3_client.delete_object(Bucket=settings.AWS_S3_BUCKET_NAME, Key=s3_key)
                return True
            except Exception:
                return False
    return False


def resolve_private_local_file(file_path: str) -> Path:
    """Resolve a document path while preventing traversal outside UPLOAD_DIR."""
    if not file_path.startswith("/uploads/documents/"):
        raise HTTPException(status_code=404, detail="Document not found")
    base_dir = Path(settings.UPLOAD_DIR).resolve()
    candidate = (base_dir / file_path.removeprefix("/uploads/")).resolve()
    if base_dir not in candidate.parents or not candidate.is_file():
        raise HTTPException(status_code=404, detail="Document not found")
    return candidate
