# College ERP System

A Django-based college management system (admin / staff / student portals) with
course–semester management, shift-based attendance, semester promotion, passed-out
records, and notifications.

> 📘 **Full architecture, styling guide, and feature/domain documentation:** see
> [`STYLING_ARCHITECTURE.md`](STYLING_ARCHITECTURE.md) (Part 1 = styling, Part 2 = features).

---

## Setup on a new device

Requirements: **Python 3.12** and **git**.

```bash
# 1. Clone the repo (use the URL from your GitHub repo page, or with the gh CLI):
gh repo clone acharyanimesh/College-ERP-System
cd College-ERP-System

# 2. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate          # macOS/Linux
# .\venv\Scripts\activate         # Windows PowerShell

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app (the database is included, so no migrate/seed needed)
python manage.py runserver
```

Then open **http://127.0.0.1:8000/** in your browser.

### Login

- **Admin (HOD):** `admin@admin.com` — *(your admin password)*
- **Seeded students:** email `firstname.lastname<n>@example.com`, password `student123`

---

## Notes

- The SQLite database (`db.sqlite3`) **is committed** so your data and logins move
  between your devices. Because of this, **don't edit the app on two devices at the
  same time** — finish on one, `git push`, then `git pull` on the other before
  continuing. Otherwise the database can conflict.
- Backup snapshots (`db.sqlite3.bak*`) and the `venv/` are git-ignored.
- This repo contains development secrets (`SECRET_KEY`, a Firebase key) — keep the
  repository **private**.

## Day-to-day git workflow

```bash
git pull            # get the latest before you start working
# ... make changes ...
git add -A
git commit -m "describe what you changed"
git push            # send it to GitHub
```
