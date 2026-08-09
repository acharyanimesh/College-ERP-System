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
   | `DJANGO_SUPERUSER_EMAIL` | your first login — see step 4 |
   | `DJANGO_SUPERUSER_PASSWORD` | a real password; it is the only account that exists |
   | `RECAPTCHA_SECRET` | leave **empty** unless you have your own key pair |

   You won't know the Vercel URL until step 3 — put a placeholder in, finish
   step 3, then come back and correct both. Django rejects logins from an
   origin missing from `DJANGO_CSRF_TRUSTED_ORIGINS`, so this one matters.

   `DATABASE_URL`, `DJANGO_DEBUG` and `RENDER_EXTERNAL_HOSTNAME` are wired up
   by the blueprint — leave them alone.

4. Every deploy runs `build.sh`: installs dependencies, `collectstatic`,
   `migrate`, then `manage.py bootstrap_admin`, which makes the database
   match `DJANGO_SUPERUSER_EMAIL` / `DJANGO_SUPERUSER_PASSWORD`.

   That command exists because **Render's Shell is a paid feature** — on the
   free plan nothing can be run by hand. `createsuperuser` was not enough on
   its own for two reasons: it refuses to run twice, so it can never repair
   an account, and the account it makes has `email_verified = False`, which
   sends the administrator to a "confirm your institutional email" screen on
   first login. On a deployment with no SMTP configured that mail goes to the
   console — the logs — and the administrator is locked out of their own
   system by a link they cannot reach.

   `bootstrap_admin` sets the role to HOD, marks the email verified, clears
   any half-finished email change, and resets the password to the variable.
   So it is also **the recovery path**: if you are ever locked out, change
   `DJANGO_SUPERUSER_PASSWORD` and redeploy. Running it repeatedly is normal;
   it never creates a second administrator.

   That one account is both a Django superuser for `/django-admin/` and the
   application's own admin in the React app. Once you are in, make a second
   admin through the UI and delete both variables — a password in a dashboard
   is a password in a dashboard.

   > Careful: if you change your admin's email **inside the app**, the
   > address in `DJANGO_SUPERUSER_EMAIL` no longer matches any account, and
   > the next deploy will create a second administrator under the old
   > address. Delete the variables, or keep them in step.

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

### reCAPTCHA is off by default, deliberately

The login page's captcha is enforced only when `RECAPTCHA_SECRET` is set on
Render **and** `VITE_RECAPTCHA_SITE_KEY` is set on Vercel. They are two
halves of one key pair and are useless apart.

It used to switch itself on whenever `DEBUG` was off — which is to say, the
moment you deployed — using a key pair hardcoded in the source and
registered to domains this deployment does not own. The widget would have
refused to render, the token would have been empty, and every login would
have been rejected with "Invalid Captcha", including yours.

To turn it on: register a pair at
<https://www.google.com/recaptcha/admin> (reCAPTCHA **v2 "I'm not a robot"**),
list your Vercel domain under *Domains*, then set both variables and
redeploy. Leave them unset and the login page simply has no captcha on it.

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
