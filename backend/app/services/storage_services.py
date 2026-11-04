import base64
import uuid
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
from app.config import settings

try:
    if settings.SUPABASE_URL and settings.SUPABASE_KEY:
        supabase: Client | None = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
    else:
        supabase = None
except Exception:
    supabase = None


async def upload_xray_image(file: UploadFile) -> str:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")

    contents = await file.read()
    file_ext = f".{file.filename.split('.')[-1]}" if file.filename and "." in file.filename else ".png"
    return await upload_image_bytes(contents, filename_prefix="xray", content_type=file.content_type, ext=file_ext)


async def upload_image_bytes(contents: bytes, filename_prefix: str = "xray", content_type: str = "image/png", ext: str = ".png") -> str:
    unique_filename = f"{filename_prefix}_{uuid.uuid4()}{ext}"

    if supabase is not None:
        try:
            supabase.storage.from_(settings.SUPABASE_BUCKET).upload(
                path=unique_filename,
                file=contents,
                file_options={"content-type": content_type}
            )
            return supabase.storage.from_(settings.SUPABASE_BUCKET).get_public_url(unique_filename)
        except Exception as exc:
            print(f"[WARN] Supabase storage upload failed ({exc}). Using inline data URI fallback.")

    encoded = base64.b64encode(contents).decode("utf-8")
    return f"data:{content_type};base64,{encoded}"
