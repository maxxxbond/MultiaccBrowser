from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.models.schemas import ProfileCreateRequest
from app.services.profile_manager import ProfileManager

router = APIRouter()
manager = ProfileManager()

class ProfileAction(BaseModel):
    profile_name: str

@router.get("/")
def read_root():
    return {"message": "Welcome to the Profile Manager API"}

@router.post("/start")
async def start_profile(data: ProfileAction):
    """Запускає профіль (браузер) у фоні."""
    return manager.start_profile(data.profile_name)

@router.post("/stop")
async def stop_profile(data: ProfileAction):
    """Зупиняє профіль (браузер)."""
    return manager.stop_profile(data.profile_name)


@router.post("/create_profile")
async def create_profile(request: ProfileCreateRequest):
    try:
        profile_name = await manager.create_profile(request.name, request.proxy_str)
        return {"message": f'Profile "{profile_name}" created!'}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error creating profile: {str(e)}")


@router.get("/list")
async def list_profiles():
    return {"profiles": manager.list_profiles()}


@router.post("/stop_all")
async def stop_all():
    """Зупиняє всі профілі."""
    manager.stop_all()
    return {"status": "All profiles stopped."}