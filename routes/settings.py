from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates
from auth import login_required

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/settings")
@login_required
async def settings(request: Request):
    return templates.TemplateResponse("settings.html", {"request": request})
