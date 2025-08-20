from fastapi import APIRouter, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
 # from auth import login_required
from services.tailscale_service import TailscaleClient

router = APIRouter()
templates = Jinja2Templates(directory="templates")

@router.get("/keys")
 # @login_required
def keys_dashboard(request: Request):
    keys = TailscaleClient.api_list_keys()
    return templates.TemplateResponse("keys.html", {"request": request, "keys": keys})

@router.post("/keys/create")
 # @login_required
def create_key(request: Request, expiry: int = Form(...), reusable: bool = Form(...), ephemeral: bool = Form(...), description: str = Form("")):
    result = TailscaleClient.api_create_key(expiry, reusable, ephemeral, description)
    return RedirectResponse("/keys", status_code=302)

@router.post("/keys/revoke")
 # @login_required
def revoke_key(request: Request, key_id: str = Form(...)):
    result = TailscaleClient.api_revoke_key(key_id)
    return RedirectResponse("/keys", status_code=302)
