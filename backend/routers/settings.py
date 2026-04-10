"""App settings endpoints."""
from fastapi import APIRouter
from models.schemas import AppSettings
from services.settings_service import load_settings, save_settings

router = APIRouter(prefix="/api/settings", tags=["settings"])


@router.get("", response_model=AppSettings)
async def get_settings():
    s = load_settings()
    # Mask sensitive values in response
    masked = s.model_dump()
    if masked["openai_api_key"]:
        masked["openai_api_key"] = masked["openai_api_key"][:8] + "..."
    if masked["naver_pw"]:
        masked["naver_pw"] = "••••••••"
    if masked["coupang_secret_key"]:
        masked["coupang_secret_key"] = masked["coupang_secret_key"][:8] + "..."
    return AppSettings(**masked)


@router.get("/raw", response_model=AppSettings)
async def get_settings_raw():
    """Return full settings (for internal use, no masking)."""
    return load_settings()


@router.post("", response_model=AppSettings)
async def update_settings(body: AppSettings):
    # Don't overwrite with masked values
    current = load_settings()
    data = body.model_dump()
    if data["openai_api_key"].endswith("..."):
        data["openai_api_key"] = current.openai_api_key
    if data["naver_pw"] == "••••••••":
        data["naver_pw"] = current.naver_pw
    if data["coupang_secret_key"].endswith("..."):
        data["coupang_secret_key"] = current.coupang_secret_key
    updated = AppSettings(**data)
    save_settings(updated)
    return updated
