# Deploying the College ERP

Two hosts, one website:

```
        browser
           |
           v
  https://<you>.vercel.app          Vercel
    /            -> React build (this is all Vercel really serves)
    /api/*       -\
    /media/*     -/  rewritten, server-side, to Render
           |
           v
  https://<you>.onrender.com        Render
    /api/v1/*    -> Django REST API
    /media/*     -> uploaded photos and deposit slips
    /django-admin/ -> Django's own admin
           |
           v
    Render Postgres
```

The rewrite is the important part. The browser only ever talks to the Vercel
domain, so the `sessionid` and `csrftoken` cookies are **first-party**. Point
the frontend straight at the Render domain instead and they become
third-party cookies, which Safari blocks outright and Chrome is in the middle
of phasing out — login would work for you and fail for a stranger, which is
the worst kind of broken.

That is also why there is no CORS configuration anywhere in this project. It
would only be needed if the browser talked to two origins, and it doesn't.

---

## 1. Rotate the secret key first

`SECRET_KEY` was hardcoded in `settings.py` for the life of this repository.
It is in the git history, the history is public, and **that key must be
treated as compromised forever** — it signs session cookies and password
reset tokens. It has been removed from the file, but generate a new one and
never reuse the old:

```bash
python -c "from django.core.management.utils import get_random_secret_key as k; print(k())"
```

Keep the output for step 2. Nothing needs it locally: with no `DATABASE_URL`
set, `manage.py runserver` and `manage.py test` still run with a throwaway
development key and `DEBUG=True`, exactly as before.

## 2. Deploy the backend to Render

1. Push this branch to GitHub (already done if you are reading this in the
   repo).
2. Render dashboard → **New** → **Blueprint** → pick this repository. It
   reads `render.yaml` and proposes a web service plus a Postgres database.
3. Fill in the variables Render marks as required:

   | Variable | Value |
   |---|---|
   | `DJANGO_SECRET_KEY` | Render generates one; or paste yours from step 1 |
   | `DJANGO_CSRF_TRUSTED_ORIGINS` | `<you>.vercel.app` — **no** `https://`, no trailing slash |
   | `FRONTEND_URL` | `https://<you>.vercel.app` — **with** the scheme |
   | `EMAIL_HOST_USER` | Gmail address used to send verification mail |
   | `EMAIL_HOST_PASSWORD` | Gmail **app password**, not the account password |
   | `DEFAULT_FROM_EMAIL` | e.g. `College ERP <noreply@yourcollege.edu.np>` |

   You won't know the Vercel URL until step 3 — put a placeholder in, finish
   step 3, then come back and correct both. Django rejects logins from an
   origin missing from `DJANGO_CSRF_TRUSTED_ORIGINS`, so this one matters.

   `DATABASE_URL`, `DJANGO_DEBUG` and `RENDER_EXTERNAL_HOSTNAME` are wired up
   by the blueprint — leave them alone.

4. First deploy runs `build.sh`: installs dependencies, `collectstatic`,
   `migrate`. The database starts **empty**, so create your first login:

   Render dashboard → the service → **Shell**:

   ```bash
   python manage.py createsuperuser
   ```

   That is a Django superuser for `/django-admin/`. The application's own
   admin (the `user_type=1` HOD role that the React app logs in as) is a
   separate thing — create one from `/django-admin/` under **Custom users**,
   with user type `1`.

5. Check it is alive: `https://<you>.onrender.com/api/v1/auth/me/` should
   answer `401` when logged out. A `401` is success here — it means Django is
   running and the API is reachable. Visiting the root gives "Frontend build
   not found", which is correct: Vercel serves the frontend, not Render.

## 3. Deploy the frontend to Vercel

1. **Edit `frontend/vercel.json` first.** Both rewrite destinations say
   `https://college-erp-api.onrender.com` — replace that with your real
   Render URL. Vercel does **not** expand environment variables inside
   `vercel.json`, so this genuinely has to be hardcoded and committed.

2. Vercel dashboard → **Add New** → **Project** → import this repository.
   - **Root Directory**: `frontend` ← easy to miss, and nothing works without it
   - Framework preset, build command and output directory come from
     `vercel.json`; leave them.
   - No environment variables are needed. `VITE_API_URL` is already `/api/v1`
     (a relative path, which is the whole point of the rewrite), and the
     build detects Vercel to set the asset base to `/` instead of Django's
     `/static/`.

3. Deploy, then go back to Render and correct `DJANGO_CSRF_TRUSTED_ORIGINS`
   and `FRONTEND_URL` with the real Vercel domain. Render redeploys itself.

4. Log in at `https://<you>.vercel.app`.

### If login returns 403

Almost always `DJANGO_CSRF_TRUSTED_ORIGINS`: it must be the bare host
(`college-erp.vercel.app`), not a URL. Django 3.1 predates the
scheme-qualified form. Note that Vercel gives every preview deployment its
own subdomain, and those are not covered — add `.vercel.app` (with the
leading dot, matching all subdomains) if you want previews to work too.

---

## The thing that will bite you: uploaded files

Profile photos and bank deposit slips are written to `media/` on the Render
instance's disk. **On the free plan that disk is wiped on every deploy.**

A lost profile photo is a nuisance. A lost deposit slip is worse: the
`FeePayment` receipt it justified is permanent and append-only, so you end up
with money recorded against a bill and no evidence behind it — precisely the
gap the verification step exists to close.

Three ways out, in increasing order of effort:

1. **Render persistent disk** — uncomment the `disk:` block in `render.yaml`.
   Requires a paid instance. Simplest, no code changes.
2. **Object storage** (Cloudinary free tier, S3, Vercel Blob) — add
   `django-storages`, set `DEFAULT_FILE_STORAGE`, and drop the manual
   `FileSystemStorage` in `main_app/api/people.py`. `DepositSlip.image` is a
   normal `FileField` and needs no change at all. Half a day, survives
   anything.
3. **Accept it while demoing** — fine if nobody is relying on the data, which
   is true right now. Just don't collect real money against it.

Also note Render's free Postgres **expires after 30 days** and is then
deleted. For anything beyond a demo, move to a paid plan or a free-forever
Postgres such as Neon, and change one environment variable (`DATABASE_URL`) —
nothing in the code knows the difference.

Free web instances also sleep after ~15 minutes idle; the first request after
that takes 30–60 seconds. Harmless for a college ERP, surprising in a demo.

---

## What runs where, and why

| Thing | Where | Why not the other one |
|---|---|---|
| React build | Vercel | Static files on a CDN is exactly what Vercel is for |
| Django API | Render | Vercel's serverless functions have a read-only filesystem and no persistent database; this app needs both |
| Postgres | Render | SQLite on any of these hosts is erased on redeploy |
| Uploads | Render disk | See the section above — this is the weak spot |

## Local development is unchanged

```bash
python manage.py runserver          # :8000, SQLite, DEBUG on
cd frontend && npm run dev          # :5173, proxies /api and /media to :8000
```

No environment variables required. The deployment settings only engage when
`DATABASE_URL` or `RENDER` is present in the environment.
