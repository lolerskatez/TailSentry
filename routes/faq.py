from fastapi import APIRouter, Request
from fastapi.templating import Jinja2Templates

router = APIRouter()
templates = Jinja2Templates(directory="templates")

from routes.user import get_current_user

@router.get("/faq")
async def faq(request: Request):
    """Display the FAQ page - accessible to all users"""
    try:
        user = get_current_user(request)
    except:
        # FAQ should be accessible even if user is not authenticated
        user = None
    
    return templates.TemplateResponse("faq.html", {
        "request": request,
        "user": user,
    })