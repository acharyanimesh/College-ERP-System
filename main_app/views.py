import os

from django.conf import settings
from django.http import HttpResponse, HttpResponseNotFound
from django.views.decorators.csrf import ensure_csrf_cookie

INDEX_PATH = os.path.join(settings.BASE_DIR, 'frontend', 'dist', 'index.html')


@ensure_csrf_cookie
def react_app(request, *args, **kwargs):
    """Serve the built React app (frontend/dist/index.html) for every
    non-API route; React Router owns the paths from there. The asset URLs
    inside it point at /static/ (vite base), served by whitenoise after
    collectstatic."""
    try:
        with open(INDEX_PATH, encoding='utf-8') as f:
            return HttpResponse(f.read())
    except FileNotFoundError:
        return HttpResponseNotFound(
            "<h3>Frontend build not found.</h3>"
            "<p>Run <code>npm run build</code> in <code>frontend/</code> "
            "(or use the Vite dev server: <code>npm run dev</code>).</p>")
