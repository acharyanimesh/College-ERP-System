# College ERP — Architecture & Styling Guide

A practical map of this project, written so you can confidently change how the
pages look without breaking functionality. It explains **how a page is built**,
**where the styles live**, and **exactly which file to edit** for any visual
change you want to make.

---

## 1. The 30-second mental model

This is a **Django** web app. Every page you see in the browser is produced by
three things working together:

```
  Django View (Python)  ──►  HTML Template  ──►  CSS file
  "what data to show"        "page structure"     "how it looks"
```

- **Views** (Python) decide *what data* a page shows. You almost never touch
  these for styling.
- **Templates** (`.html`) decide the *structure / markup* of a page. Edit these
  to move things around, add a card, change text, etc.
- **CSS** decides *colors, spacing, fonts, shadows* — the actual "look".
  **This is the file you'll edit most for styling.**

> 🎯 **The single most important file for styling:**
> `main_app/static/dist/css/erpnext-style.css`

Almost the entire visual theme is controlled by that one stylesheet, and the
top of it has CSS variables (colors, sizes) you can change in one place to
restyle the whole app.

---

## 2. Project layout (only what matters)

```
College-ERP/
├── manage.py                      # Django entry point (run the server with this)
├── db.sqlite3                     # The database (data, not styling)
├── requirements.txt               # Python dependencies
│
├── college_management_system/     # Project CONFIG (not your app code)
│   ├── settings.py                # Global settings: installed apps, static paths, DB
│   └── urls.py                    # Top-level URL routes → main_app
│
└── main_app/                      # ★ THE ACTUAL APP — everything lives here
    ├── urls.py                    # Maps URLs → view functions (the page list)
    ├── views.py                   # Login / logout / shared views
    ├── hod_views.py               # Admin (HOD) pages logic
    ├── staff_views.py             # Staff pages logic
    ├── student_views.py           # Student pages logic
    ├── models.py                  # Database tables (Student, Staff, Course…)
    ├── forms.py                    # Form definitions
    ├── middleware.py              # Login/redirect rules
    │
    ├── templates/                 # ★ ALL HTML PAGES (structure)
    │   ├── main_app/              #   shared layout: base, login, sidebar
    │   ├── hod_template/          #   admin pages
    │   ├── staff_template/        #   staff pages
    │   ├── student_template/      #   student pages
    │   └── registration/          #   password-reset pages
    │
    └── static/                    # ★ ALL CSS / JS / IMAGES (look & behavior)
        ├── dist/css/              #   stylesheets  ← you edit erpnext-style.css here
        ├── dist/js/               #   scripts
        ├── image/                 #   logos, favicon
        └── plugins/               #   third-party libs (FontAwesome, jQuery, Bootstrap…)
```

Ignore for styling purposes: `venv/` (Python environment), `media/`
(uploaded files like profile pics), `reports_and _resource/`, `__pycache__/`.

---

## 3. How one page is assembled (the layout system)

Django uses **template inheritance**. There is one master layout, and every
page "fills in the blanks" of that master. This is why all pages share the same
navbar and sidebar — they're defined once.

### The master layout: `main_app/templates/main_app/base.html`

This file defines the frame that wraps **every logged-in page**:

```
┌─────────────────────────────────────────────────────────┐
│  NAVBAR  (top bar: brand, dark-mode toggle, user avatar) │  ← <nav class="erpnext-navbar">
├──────────┬──────────────────────────────────────────────┤
│          │  PAGE HEADER (title + breadcrumb)             │  ← <div class="page-header">
│ SIDEBAR  ├──────────────────────────────────────────────┤
│ (menu)   │                                              │
│          │  CONTENT  ← {% block content %} goes here     │  ← <main class="erpnext-main">
│          │  (this is what each individual page fills in) │
│          │                                              │
└──────────┴──────────────────────────────────────────────┘
```

Key pieces inside `base.html`:

| Region | HTML marker | What it is |
|--------|-------------|-----------|
| Top bar | `<nav class="erpnext-navbar">` | Brand name, dark-mode switch, user name + avatar |
| Sidebar shell | `<aside class="erpnext-sidebar">` | Container; its links come from an included file |
| Page header | `<div class="page-header">` | The page title + breadcrumb trail |
| Content slot | `{% block content %}{% endblock %}` | **Where each page's unique content is injected** |

### The sidebar menu: `main_app/templates/main_app/erpnext_sidebar.html`

`base.html` pulls the menu links from this file via
`{% include "main_app/erpnext_sidebar.html" %}`. It shows **different menu items
based on who is logged in** (`user.user_type`):

- `'1'` → Admin / HOD menu
- `'2'` → Staff menu
- `'3'` → Student menu

👉 To **add, remove, or rename a sidebar link**, edit this file.

### An individual page: e.g. the admin dashboard

`main_app/templates/hod_template/home_content.html` starts with:

```django
{% extends 'main_app/base.html' %}      ← "use the master layout"
{% block page_title %}Dashboard{% endblock %}   ← fills the header title
{% block content %} ... cards, charts ... {% endblock %}  ← fills the content slot
```

So a page only contains its *own* unique content; the navbar/sidebar/header come
from `base.html` automatically.

> **Almost every page in the app extends `main_app/base.html`.** That's why a
> change to `base.html` or to `erpnext-style.css` instantly affects all pages.

---

## 4. Where styling actually comes from

Loaded by `base.html` (in `<head>`), in this order:

1. **`dist/css/erpnext-style.css`** ★ — the custom theme. **99% of your edits go here.**
2. **FontAwesome** (`plugins/fontawesome-free/...`) — the icons (`<i class="fas fa-...">`).
3. **Bootstrap 5** (from a CDN) — grid system + base components (`row`, `col`, `btn`, `alert`).
4. **Chart.js** (CDN) — dashboard charts.

> ⚠️ The folder `dist/css/adminlte.*` and `dist/css/alt/*` and `dist/css/style.css`
> are **leftovers from the old theme (AdminLTE)** and are **not loaded** by the
> current pages. Don't waste time editing those — they do nothing now. The live
> theme is `erpnext-style.css`.

### 4a. The control panel: CSS variables (`:root`)

At the very top of `erpnext-style.css` is a `:root` block. **Change a value here
and it updates everywhere that uses it** — the fastest way to re-skin the app:

```css
:root {
  --primary-color: #5e64ff;   /* main brand/accent color (buttons, links, active menu) */
  --secondary-color: #8d99ae;
  --success-color: #28a745;   /* green */
  --danger-color:  #dc3545;   /* red   */
  --warning-color: #ffc107;   /* yellow*/
  --info-color:    #17a2b8;   /* teal  */
  --light-color:   #f8f9fc;   /* page background */
  --dark-color:    #262626;   /* main text color  */
  --border-color:  #d1d8dd;   /* card / table borders */
  --text-muted:    #8d99ae;   /* secondary text */
  --sidebar-width: 240px;     /* how wide the left menu is */
  --navbar-height: 60px;      /* how tall the top bar is  */
}
```

**Example — rebrand to green:** change `--primary-color` to `#2e7d32`. Done —
buttons, active links, the navbar brand, stat numbers, etc. all follow.

### 4b. Section map of `erpnext-style.css`

The file is organized into clearly-commented sections (`/* ... */`). Jump to the
section for whatever you want to change:

| Want to change… | Look for this comment section |
|---|---|
| Page background, base fonts | `/* Reset and base styles */` |
| Top bar | `/* Header/Navbar */` |
| Logout button | `/* Logout Button Styling */` |
| Left menu container | `/* Sidebar */` |
| Menu links / icons / active state | `/* Navigation Menu */`, `/* Submenu */` |
| Content area width/padding | `/* Main Content */` |
| Page title + breadcrumb | `/* Page Header */` |
| Card panels | `/* Cards */` |
| Dashboard number tiles | `/* Stats Cards */` |
| Buttons | `/* Buttons - ERPNext Style */` |
| Form inputs | `/* Forms */` |
| Tables | `/* Tables */`, `/* Remove borders... */` |
| Alert/notification banners | `/* Alerts */` |
| Login screen | `/* Login Page */` |
| Mobile / tablet behavior | `/* Responsive Design */`, `/* Mobile responsive... */` |
| Animations | `/* Animation and transitions */` |
| **Dark mode** (whole bottom half) | `/* Dark Mode Styles */` and every `/* Dark mode support... */` |
| Dark-mode toggle switch itself | `/* Dark Mode Toggle Button - Capsule Slider */` |
| Badges | `/* Badge styles for light mode */`, `/* Dark mode badge styles */` |

> 🌓 **Dark mode note:** the app has a working dark mode, toggled by the switch
> in the navbar (state saved in the browser). Styles activate when `<body>` gets
> the class `dark-mode`. **If you change a light-mode color, find the matching
> `/* Dark mode support... */` section and update its dark version too**, or the
> two modes will look inconsistent.

---

## 5. "I want to change X" — quick recipes

| Goal | File to edit | What to do |
|---|---|---|
| Recolor the whole app | `erpnext-style.css` → `:root` | Change `--primary-color` (and friends) |
| Make the sidebar wider/narrower | `erpnext-style.css` → `:root` | Change `--sidebar-width` |
| Restyle buttons | `erpnext-style.css` → `/* Buttons */` | Edit `.btn`, `.btn-primary`, etc. |
| Restyle cards | `erpnext-style.css` → `/* Cards */` | Edit `.card`, `.card-header` |
| Change the navbar look | `erpnext-style.css` → `/* Header/Navbar */` | Edit `.erpnext-navbar` rules |
| Change the brand text "College ERP" | `base.html` (+ `erpnext_sidebar.html`, login pages) | Edit the literal text |
| Add / rename / remove a menu item | `erpnext_sidebar.html` | Add/edit a `<div class="nav-item">` block |
| Change layout shared by all pages | `base.html` | Edit navbar / header / content wrapper |
| Restyle one specific page only | that page's `.html` in `templates/<role>_template/` | Edit its `{% block content %}` markup, or add a `{% block custom_css %}` |
| Change the login screen | `templates/main_app/login.html` + `/* Login Page */` in CSS | Markup + styles |
| Swap the logo / favicon | `static/image/` | Replace the image files |
| Tweak dark mode colors | `erpnext-style.css` → `/* Dark Mode Styles */` | Edit the `.dark-mode ...` rules |

### Page-specific styling without touching the global CSS

Every page can inject its own CSS because `base.html` provides these empty
"blocks":

```django
{% block custom_css %}
  <style>
    /* styles that apply ONLY to this page */
  </style>
{% endblock %}

{% block custom_js %}
  <script> /* page-only JS */ </script>
{% endblock %}
```

Use this when you want to experiment on a single page without risking the rest
of the app.

---

## 6. Which template renders which URL

Pages are wired up in `main_app/urls.py` (URL → view function), and each view
renders a template. Roles map to folders:

- **Admin / HOD** → `hod_views.py` → `templates/hod_template/`
- **Staff** → `staff_views.py` → `templates/staff_template/`
- **Student** → `student_views.py` → `templates/student_template/`
- **Login / shared** → `views.py` → `templates/main_app/`

To find the template behind a page: open `urls.py`, find the URL name → it points
to a function in one of the `*_views.py` files → that function ends with
`render(request, '<folder>/<file>.html', ...)`. That `.html` is the page to edit.

The three dashboards specifically:

| Role | URL name | Template |
|---|---|---|
| Admin | `admin_home` | `hod_template/home_content.html` |
| Staff | `staff_home` | `staff_template/home_content.html` |
| Student | `student_home` | `student_template/home_content.html` |

---

## 7. Files you can safely ignore (legacy / unused)

These are remnants of the previous AdminLTE theme. They are **not loaded** by the
current pages, so editing them changes nothing. Knowing this saves you confusion:

- `static/dist/css/adminlte.*`, `static/dist/css/alt/*`, `static/dist/css/style.css`
- `templates/main_app/erpnext_base.html` (an alternate base; live base is `base.html`)
- `templates/main_app/erpnext_login.html` (live login is `login.html`)
- `templates/main_app/sidebar_template.html`, `templates/main_app/index.html`,
  `templates/main_app/footer.html`, `templates/main_app/form_template.html`
- `templates/hod_template/erpnext_home_content.html`,
  `templates/hod_template/erpnext_home_fixed.html` (live admin dashboard is `home_content.html`)
- `templates/registration/base.html` (the live one is `registration/erpnext_base.html`)

> Tip: before editing a template, confirm it's the live one by checking that a
> view in a `*_views.py` actually `render()`s it (see §6).

---

## 8. Seeing your changes

1. Activate the environment and run the dev server:
   ```bash
   source venv/bin/activate
   python manage.py runserver
   ```
2. Open `http://127.0.0.1:8000/` and log in.
3. Edit `erpnext-style.css` (or a template) → save → **hard-refresh** the browser
   (`Cmd+Shift+R`) to bypass the CSS cache.

> CSS/template edits don't require restarting the server — just refresh. (If a
> CSS change stubbornly won't appear, it's browser caching; hard-refresh.)

### A note on `collectstatic` (production only)

In development (`DEBUG = True`, which is the current setting) Django serves CSS
straight from `static/`, so your edits show up on refresh. WhiteNoise is still
configured (`whitenoise.middleware.WhiteNoiseMiddleware` + `CompressedManifestStaticFilesStorage`
in `settings.py`), so for a production build you'd run `python manage.py collectstatic`.
You do **not** need that while developing locally.

> **Deployment note:** the old Heroku deploy files (`Procfile`, `LICENSE`) were
> **removed**. This project is no longer deployed as a hosted service — it is run
> locally and **shared between devices via git with the SQLite DB committed** (see
> §20). `gunicorn`/`whitenoise` remain in `requirements.txt` but aren't wired to a
> host anymore.

---

## 9. Cheat sheet — the five files that matter for styling

1. **`main_app/static/dist/css/erpnext-style.css`** — the entire theme. Start at `:root`.
2. **`main_app/templates/main_app/base.html`** — shared layout (navbar, header, content frame).
3. **`main_app/templates/main_app/erpnext_sidebar.html`** — the menu links.
4. **`main_app/templates/main_app/login.html`** — the login screen.
5. **`main_app/templates/<role>_template/*.html`** — individual page content.

Everything else is data, configuration, or unused legacy.

---
---

# Part 2 — Application Features & Domain Logic

> This part documents the **functional features** built on top of the base app
> (the styling guide above is Part 1). It is the source of truth for *how the
> academic/promotion/attendance/notification logic works and where it lives*, so
> work can continue without prior chat context.

## 10. Academic data model (key fields added)

All models are in `main_app/models.py`. Migrations `0014`–`0017` added the fields below.

- **`Course`**: `name`, **`abbreviation`** (short form e.g. `"BE-IT"`, migration `0017`),
  `semesters` (total # of semesters, e.g. 8).
  - Property **`course.short_name`** → abbreviation, or full name if blank.
  - Property **`course.name_with_abbr`** → `"Full Name (ABBR)"`.
- **`Subject`** ↔ **`Course`** via the **`CourseSubject`** through-model
  (`course`, `subject`, `semester`, `unique_together=(course, subject)`).
  Teaching is **per shift**: `CourseSubject.morning_staff` / `day_staff`
  (FK→Staff, SET_NULL). Helper `cs.staff_for_shift(shift)`.
- **`Student`**: `admin` (OneToOne→CustomUser, CASCADE), `registration_number`
  (`XXXX-XXXX-XXXX`, unique), `roll_number` (6 digits), `course`, `session`,
  `shift` (`"morning"`/`"day"`), **`current_semester`** (PositiveSmallInt, default 1,
  migration `0014`), **`passed_out`** (bool, default False) + **`passed_out_date`**
  (migration `0016`).
- **`Session`**: `start_year`, `end_year` (DateFields). An academic year = **two
  semesters**; a session ≈ a 4-year intake.
- **`Attendance`**: `session`, `subject`, `shift`, `date`, **`locked`** (bool,
  migration `0015`). **`AttendanceReport`**: `student`, `attendance`, `status`,
  `late`. NOTE: `AttendanceReport.student` is `on_delete=DO_NOTHING` (matters when
  deleting students — delete AttendanceReport rows first).
- **Shift**: `SHIFT_CHOICES = (("morning","Morning Shift"),("day","Day Shift"))`.
  `Staff.teaches_morning` / `teaches_day` booleans; `staff.shifts` / `shifts_display`.

## 11. Course abbreviations (used everywhere except Manage Courses)

Goal: long course names congested tables/banners, so the **abbreviation is shown
everywhere**, with the full name kept in a `title="..."` hover tooltip. The **only**
place that shows the full name + abbr is the **Manage Courses list page**
(`manage_course.html`, uses `course.name_with_abbr`).

- Templates use `course.short_name` (cards, tables, attendance dropdowns, banners).
- View-built `page_title` banners/messages in `hod_views.py` use `course.short_name`.
- Abbreviation is an editable field on **Add/Edit Course** (`CourseForm`, fields
  `['name','abbreviation','semesters']`; set in `add_course`/`edit_course`).
- Current values: **BE-IT**, **BE Civil**, **BE Software**.

## 12. Manage Students navigation + cascade promotion

**Nav flow (HOD):** `manage_student` → `manage_student_by_course` (semester cards)
→ `manage_student_by_course_semester` (shift cards) → `manage_student_by_course_semester_shift`
(student list). Templates: `manage_student.html`, `student_semester_list.html`,
`student_shift_list.html`, `student_list_by_course.html`. All active-student
queries filter **`passed_out=False`**.

**Cascade promotion** (`promote_class` view + helper `_cascade_promote_course(course, from_semester)`):
- Promoting semester **N** advances **every semester ≥ N** in that course (both
  shifts) up by one via `update(current_semester=F('current_semester')+1)`, so a
  lower batch never mixes into the batch above it.
- Students at the **final semester** (`course.semesters`) are **not** moved up —
  they are marked `passed_out=True, passed_out_date=today` (graduated).
- The semester-list page shows **one button per populated semester**: "Promote
  Sem N & above" (non-final) or "Pass out Sem N" (final). Empty semesters show
  "Semester currently not active". (The old per-shift promote button + the
  `promote_shift` view/URL were **removed**.)

## 13. Passed-out students

- `passed_out` students are **excluded from all active queries** (manage-student
  counts/lists, attendance `get_students`/cohort, dashboard totals — everywhere via
  `passed_out=False`). Their `AttendanceReport` history is kept intact.
- **Passed Out Students** section (sidebar item under Manage Students):
  `passed_out_students` (course list) → `passed_out_by_course` (session list) →
  `passed_out_by_session` (student table). URLs under `student/passed-out/...`.
  Templates `passed_out_course_list.html`, `passed_out_session_list.html`,
  `passed_out_student_list.html`. The student table shows **both shifts together**
  (no shift split), ordered alphabetically.

## 14. New-session intake auto-promotion (`add_student`)

When a first-year student is added (in `add_student`, `current_semester==1`) for a
session that is **new to that course** AND the course already has students of an
**older** session, the whole course is **cascade-promoted first**
(`_cascade_promote_course(course, 1)`) so the new intake starts in an empty Sem 1.
Conditions (all required):
- `not already_this_session` (no active student of this course already has this session), and
- `older_exists` (`Student.objects.filter(course=course, passed_out=False, session__start_year__lt=session.start_year)`).

This means only the **first** student of a new intake triggers it; older-session
backfills never promote. (It is keyed off the **session being new+newer**, NOT off
Sem 1 being occupied — an earlier version checked Sem-1 occupancy and silently
skipped promotion once Sem 1 had been vacated.)

**Sem-1 closed after a batch progresses** (also `add_student`): once a
`(course, session)` batch has moved past Semester 1, that session's Semester 1 is
**closed** — a new student of that session can no longer be added at Sem 1; they
must join the batch at its **current** semester. Rule: if `new_sem == 1` and
`Student.objects.filter(course, session, passed_out=False)` exists but has **none**
at `current_semester=1`, the add is **rejected** with an error naming the batch's
current semester. Sem 1 stays open while the batch is still running in Sem 1, and
a brand-new session still starts at Sem 1 (handled by the intake auto-promotion
above).

## 15. Staff attendance — Take / Update / View (`staff_views.py`, `views.py`)

Shared picker built by `_attendance_picker_context(staff)`. Picker order:
**Shift → Subject (clickable buttons, filtered by shift) → Course → Semester**.
The **Semester** dropdown replaced the old Session-Year selector and **auto-sets**
from the subject's per-course `CourseSubject.semester` (JS `data-assignments`).

- **Take Attendance** (`staff_take_attendance` / `get_students` / `save_attendance`):
  `get_students` filters by course + **`current_semester`** + shift + `passed_out=False`
  (so promoted students don't show for a lower-semester subject). **No status is
  preselected**; JS blocks saving until every student is marked. `save_attendance`
  **derives `Attendance.session`** from the cohort's `Student.session` (returns
  `NO_SESSION` if unset) and validates the teacher is assigned for that
  course/semester/shift.
- **Update Attendance** (`staff_update_attendance` / `get_attendance` in `views.py` /
  `update_attendance`): saving an update **locks** the record (`Attendance.locked=True`);
  it then can't be edited again (`update_attendance` returns `LOCKED`).
  `get_attendance` only lists **unlocked** records here.
- **View Attendance** (`staff_view_attendance`, read-only): sidebar item under
  Update Attendance; same picker; shows status as colored badges. Calls
  `get_attendance` with `include_locked=1` to show **all** dates (locked ones
  labelled "— confirmed"). Template `staff_view_attendance.html`.
- Fetched/displayed students show **roll number** (not registration), name as
  **"First Last"**, ordered alphabetically by first then last name.

## 16. Notify Student / Notify Staff (`hod_views.py`)

- **Notify Staff**: names shown "First Last", ordered alphabetically.
- **Notify Student**: rebuilt to mirror Manage Students — landing page
  (`admin_notify_student`) has a **global student search** (across all active
  students) **plus** course cards → `notify_student_by_course` (semester cards) →
  `notify_student_by_semester` (student list, both shifts together). Course shown
  as abbreviation; names "First Last", alphabetical; passed-out excluded. The
  send modal is a shared partial `hod_template/_notify_student_modal.html`
  (reused by the landing search and the per-semester list).

## 17. Migrations added (in order)

| Migration | Adds |
|---|---|
| `0014_student_current_semester` | `Student.current_semester` |
| `0015_attendance_locked` | `Attendance.locked` |
| `0016_auto_20260625_2320` | `Student.passed_out`, `Student.passed_out_date` |
| `0017_course_abbreviation` | `Course.abbreviation` |

## 18. Current seed data & credentials (as of last session)

- **Admin (HOD) login:** `admin@admin.com` (password set by you).
- **Seeded students:** password **`student123`**; email pattern
  `firstname.lastname<n>@example.com`. Nepali names/addresses, 10-digit phones
  (start `98`/`97`).
- **3 courses** (BE-IT, BE Civil, BE Software, 8 semesters each), **13 staff**,
  **3 sessions** (2022-2026, 2023-2027, 2024-2028 — note: session **IDs are not
  stable** across recreation; look them up by `start_year.year`).
- **270 students** seeded into **odd semesters only**: Sem 1 / 3 / 5, each with
  15 morning + 15 day per course. Session↔semester mapping: **Sem 1 → 2024-2028**,
  **Sem 3 → 2023-2027**, **Sem 5 → 2022-2026** (one academic year = two semesters
  apart).

## 19. Conventions (data scripts, backups, running)

- **Run app / one-off scripts:** `source venv/bin/activate` first (Django 3.1).
  Standalone scripts need `sys.path.insert(0, "<project root>")` before
  `django.setup()`. `python manage.py runserver` (auto-reloads on edits).
- **Bulk DB changes:** back up first — `cp db.sqlite3 db.sqlite3.bak-<reason>-<ts>`.
  Wrap mutations in `transaction.atomic()`. To **verify behavior without
  committing**, run inside `with transaction.atomic(): ... raise <Rollback>` and
  catch it (used throughout to test promotion/intake against the live DB safely).
- **Deleting students:** delete `AttendanceReport` first (it's `DO_NOTHING`), then
  `CustomUser.objects.filter(user_type='3').delete()` (cascades Student + children).
- **Seeding speed:** hash the shared password **once**
  (`make_password(...)`) and reuse the string — per-user hashing is the bottleneck.
  Ensure any `unique_*` helper actually increments (a missing `n += 1` caused an
  infinite loop once).

## 20. Repo, environment & cross-device workflow

How the project is packaged and moved between machines (newer than the rest of
Part 2; see also `README.md`, which is the user-facing version of this).

- **Python version:** **3.12** (local `venv` runs 3.12.3). Django is **3.1.1**
  (pinned, old — keep code compatible with it). Deps are pinned in
  `requirements.txt`; setup is `python3 -m venv venv` → `source venv/bin/activate`
  → `pip install -r requirements.txt` → `python manage.py runserver`.
- **The database is committed.** `db.sqlite3` is **intentionally tracked in git**
  (the `.gitignore` says so) so data + the admin login travel between devices. No
  `migrate`/seed step is needed on a fresh clone — the data is already there.
  - ⚠️ **Consequence:** don't edit on two devices at once. Finish on one →
    `git push` → `git pull` on the other before continuing, or the DB conflicts.
  - **Backups** (`db.sqlite3.bak*`) and `venv/` are git-ignored.
- **Secrets in the repo:** `SECRET_KEY` and a Firebase key live in the code, so the
  **repository must stay private**.
- **`README.md`** is the onboarding doc (clone → venv → install → run, login
  credentials, and the git workflow). This file (`STYLING_ARCHITECTURE.md`) is the
  deep reference it links to.
- **Removed files:** `Procfile` and `LICENSE` were deleted — the project is no
  longer set up for Heroku deployment (see the deployment note in §8).
