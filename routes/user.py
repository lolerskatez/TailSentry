# Change password endpoints
@router.get("/change-password")
def change_password_form(request: Request, user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": None})

@router.post("/change-password")
def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), user=Depends(get_current_user)):
    if not user:
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
    from auth_user import verify_user, get_db, pwd_context

    import os
    from fastapi import APIRouter, Request, Form, Depends, Response, status
    from fastapi.responses import RedirectResponse, HTMLResponse
    from fastapi.templating import Jinja2Templates
    from starlette.middleware.sessions import SessionMiddleware
    from auth_user import create_user, verify_user, get_user, list_users, delete_user, init_db

    router = APIRouter()
    templates = Jinja2Templates(directory="templates")

    # Initialize DB on startup
    init_db()

    SESSION_SECRET = os.environ.get("SESSION_SECRET", "changeme")

    def get_current_user(request: Request):
        username = request.session.get("user")
        if username:
            return get_user(username)
        return None

    @router.get("/login")
    def login_form(request: Request):
        return templates.TemplateResponse("login.html", {"request": request, "error": None})

    @router.post("/login")
    def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
        user = verify_user(username, password)
        if user:
            request.session["user"] = user["username"]
            return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

    @router.get("/logout")
    def logout(request: Request, response: Response):
        request.session.clear()
        return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

    @router.get("/register")
    def register_form(request: Request):
        return templates.TemplateResponse("register.html", {"request": request, "error": None})

    @router.post("/register")
    def register(request: Request, username: str = Form(...), password: str = Form(...)):
        if create_user(username, password):
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})

    @router.get("/users")
    def users(request: Request, user=Depends(get_current_user)):
        if not user or user["role"] != "admin":
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        return templates.TemplateResponse("users.html", {"request": request, "users": list_users()})

    @router.post("/users/delete")
    def delete_user_route(request: Request, username: str = Form(...), user=Depends(get_current_user)):
        if not user or user["role"] != "admin":
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        delete_user(username)
        return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)

    # Change password endpoints
    @router.get("/change-password")
    def change_password_form(request: Request, user=Depends(get_current_user)):
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": None})

    @router.post("/change-password")
    def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), user=Depends(get_current_user)):
        if not user:
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
        from auth_user import verify_user, get_db, pwd_context

        import os
        from fastapi import APIRouter, Request, Form, Depends, Response
        from fastapi.responses import RedirectResponse
        from starlette import status
        from fastapi.templating import Jinja2Templates
        from auth_user import create_user, verify_user, get_user, list_users, delete_user, init_db

        router = APIRouter()
        templates = Jinja2Templates(directory="templates")

        # Initialize DB on startup
        init_db()

        SESSION_SECRET = os.environ.get("SESSION_SECRET", "changeme")

        def get_current_user(request: Request):
            username = request.session.get("user")
            if username:
                return get_user(username)
            return None

        @router.get("/login")
        def login_form(request: Request):
            return templates.TemplateResponse("login.html", {"request": request, "error": None})

        @router.post("/login")
        def login(request: Request, response: Response, username: str = Form(...), password: str = Form(...)):
            user = verify_user(username, password)
            if user:
                request.session["user"] = user["username"]
                return RedirectResponse(url="/", status_code=status.HTTP_302_FOUND)
            return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid credentials"})

        @router.get("/logout")
        def logout(request: Request, response: Response):
            request.session.clear()
            return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)

        @router.get("/register")
        def register_form(request: Request):
            return templates.TemplateResponse("register.html", {"request": request, "error": None})

        @router.post("/register")
        def register(request: Request, username: str = Form(...), password: str = Form(...)):
            if create_user(username, password):
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
            return templates.TemplateResponse("register.html", {"request": request, "error": "Username already exists"})

        @router.get("/users")
        def users(request: Request, user=Depends(get_current_user)):
            if not user or user["role"] != "admin":
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
            return templates.TemplateResponse("users.html", {"request": request, "users": list_users()})

        @router.post("/users/delete")
        def delete_user_route(request: Request, username: str = Form(...), user=Depends(get_current_user)):
            if not user or user["role"] != "admin":
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
            delete_user(username)
            return RedirectResponse(url="/users", status_code=status.HTTP_302_FOUND)

        @router.get("/change-password")
        def change_password_form(request: Request, user=Depends(get_current_user)):
            if not user:
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
            return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": None})

        @router.post("/change-password")
        def change_password(request: Request, old_password: str = Form(...), new_password: str = Form(...), user=Depends(get_current_user)):
            if not user:
                return RedirectResponse(url="/login", status_code=status.HTTP_302_FOUND)
            from auth_user import verify_user, get_db, pwd_context
            # Verify old password
            if not verify_user(user["username"], old_password):
                return templates.TemplateResponse("change_password.html", {"request": request, "error": "Current password is incorrect.", "success": None})
            # Update password
            conn = get_db()
            c = conn.cursor()
            c.execute('UPDATE users SET password_hash = ? WHERE username = ?', (pwd_context.hash(new_password), user["username"]))
            conn.commit()
            conn.close()
            return templates.TemplateResponse("change_password.html", {"request": request, "error": None, "success": "Password changed successfully."})
