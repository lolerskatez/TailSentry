# CSRF Cookie Troubleshooting Checklist

If your CSRF cookie is not being set in the browser, check the following:

1. **Direct Access:**
   - Access the `/users` page directly in your browser (not via redirect).
   - Perform a hard refresh (Ctrl+Shift+R or Cmd+Shift+R).

2. **Browser Developer Tools:**
   - Open DevTools (F12 or right-click > Inspect).
   - Go to the Application/Storage tab > Cookies > [your site].
   - Look for a cookie named `csrf_token`.

3. **Check Response Headers:**
   - In the Network tab, select the request for `/users`.
   - Check the Response Headers for a `Set-Cookie: csrf_token=...` header.

4. **Reverse Proxy/Server Configuration:**
   - If using nginx, Apache, or another proxy, ensure it is not stripping or blocking `Set-Cookie` headers.
   - Make sure headers like `Set-Cookie` are allowed through any proxy config.

5. **Cookie Attributes:**
   - The CSRF cookie is set with `samesite=strict` and `httponly=false`.
   - If your site is accessed via a different domain or port, `samesite=strict` may prevent the cookie from being sent.
   - Try changing `samesite` to `lax` in the middleware for testing.

6. **HTTPS/HTTP:**
   - If running locally, the cookie should be set with `secure=false`.
   - If using HTTPS, ensure the scheme is detected correctly in the middleware.

7. **Browser Extensions:**
   - Disable privacy or security extensions that might block cookies.

8. **Server Logs:**
   - Check your server logs for any CSRF or cookie-related warnings.

---

If the cookie is still not set after these checks, consider temporarily relaxing the `samesite` attribute in your CSRF middleware for debugging:

```
# In middleware/csrf.py, change:
samesite="strict"
# to:
samesite="lax"
```

Then restart your server and try again.
