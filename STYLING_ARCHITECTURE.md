# College ERP — Architecture & Styling Guide

A practical map of this project, written so you can confidently change how the
pages look — or find where a feature lives — without breaking functionality.

> **This file was rewritten after the React migration.** The app used to be a
> server-rendered Django-template site; it is now a **React + Vite single-page
> app** talking to a **Django REST Framework API**. If you find an old copy of
> this doc (or old advice) that mentions `hod_views.py`, `templates/hod_template/`,
> or AdminLTE — that's the pre-migration architecture and no longer applies.

---

## 1. The 30-second mental model

```
  React SPA (Vite build)  ──HTTP/JSON──►  Django REST API (/api/v1/)  ──►  SQLite
  "what you see & click"                   "business logic, auth, data"
```

- **`frontend/`** — a React app (Vite). Every screen (dashboards, forms, lists)
  is a React component. **This is what you edit for anything visual.**
- **`main_app/api/`** — a Django REST Framework API mounted at `/api/v1/`. Pure
  JSON endpoints; no HTML, no styling. You only touch this for business logic
  or new data.
- **Django itself** also serves three small things that are *not* React:
  the built SPA's `index.html` (catch-all route), the Django admin site
  (`/django-admin/`), and the password-reset flow (`/accounts/...`, still
  server-rendered templates).

> 🎯 **The single most important file for styling:**
> `frontend/src/assets/css/erpnext-style.css`
>
> Nearly the entire visual theme is controlled by that one stylesheet, and the
> top of it has CSS variables (colors, fonts, sizes) you can change in one
> place to restyle the whole app.

---

## 2. Project layout (only what matters)

```
College-ERP-System/
├── manage.py                        # Django entry point
├── db.sqlite3                       # The database (data, not styling)
├── requirements.txt                 # Python dependencies
│
├── college_management_system/       # Project CONFIG
│   ├── settings.py                  # Installed apps, static paths, DB, DRF config
│   └── urls.py                      # /, /api/v1/, /django-admin/, /accounts/
│
├── main_app/                        # ★ DJANGO APP — data model + API + admin
│   ├── models.py                    # Database tables (Student, Staff, Course…)
│   ├── forms.py                     # Server-side validation (reused by the API)
│   ├── views.py                     # Just react_app: serves the SPA's index.html
│   ├── urls.py                      # "" (SPA catch-all) is here; API is separate
│   ├── EmailBackend.py              # Login by email instead of username
│   ├── api/                         # ★ THE JSON API (DRF), mounted at /api/v1/
│   │   ├── urls.py                  #   route list — start here to find an endpoint
│   │   ├── auth.py                  #   login / logout / me / check-email
│   │   ├── dashboard.py             #   admin/staff/student dashboard stats
│   │   ├── students.py, staff.py    #   admin management CRUD + drill-downs
│   │   ├── academics.py             #   courses / subjects / sessions
│   │   ├── attendance.py            #   take / update / view attendance
│   │   ├── results.py               #   staff result entry, student results
│   │   ├── leave_feedback.py        #   leave applications + feedback (staff/student)
│   │   ├── notifications.py         #   admin → staff/student notifications
│   │   ├── books.py                 #   library
│   │   ├── serializers.py           #   dict-builders that shape JSON responses
│   │   └── permissions.py           #   IsAdmin / IsStaff / IsStudent
│   ├── templates/
│   │   └── registration/            #   password-reset pages ONLY (still server-rendered)
│   └── static/                      #   assets for the templates above (see §4c)
│
└── frontend/                        # ★ THE REACT APP — everything you SEE lives here
    ├── index.html                   #   HTML shell + Google Fonts (Cinzel, Jost)
    ├── vite.config.js               #   dev proxy to Django; prod base path /static/
    ├── package.json                 #   JS dependencies
    ├── dist/                        #   `npm run build` output (gitignored)
    └── src/
        ├── main.jsx                 #   CSS import order + React root
        ├── App.jsx                  #   route table (URL → page component)
        ├── api/                     #   one file per backend resource — axios calls only
        ├── context/AuthContext.jsx  #   who's logged in (replaces request.user)
        ├── layouts/                 #   Layout, Navbar, Sidebar, Watermark, sidebarMenu
        ├── components/              #   shared building blocks (forms, ListCard, charts, Modal)
        ├── hooks/useApi.js          #   the `{data, loading, error, reload}` fetch hook
        ├── pages/                   #   one folder per role: admin/, staff/, student/, shared/
        └── assets/
            ├── css/erpnext-style.css     # ★ THE THEME — edit this for styling
            ├── image/brand-*.png         #   logo, watermark, favicon source art
            └── fontawesome-free/         #   icon font (self-hosted, not a CDN)
```

Ignore for styling purposes: `.venv/` (Python environment), `media/` (uploaded
profile pics), `reports_and _resource/` (a project report PDF), `__pycache__/`,
`static/` at the repo root (that's `collectstatic`'s output — see §8, it's
regenerated, never hand-edited).

---

## 3. How one page is assembled (the React layout system)

There is one shared "shell" component, and every page renders inside it — the
React equivalent of Django template inheritance.

### The shell: `frontend/src/layouts/Layout.jsx`

Wraps **every logged-in page** (mounted once by the `/*` protected route in
`App.jsx`):

```
┌─────────────────────────────────────────────────────────┐
│  NAVBAR  (brand icon + name, sidebar toggle, logout)     │  ← <Navbar>
├──────────┬──────────────────────────────────────────────┤
│          │  PAGE HEADER (title + breadcrumb)             │  ← .page-header
│ SIDEBAR  ├──────────────────────────────────────────────┤
│ (menu)   │                                              │
│          │  CONTENT  ← <Outlet /> renders the page here  │  ← <main class="erpnext-main">
│          │  (each page component is React Router's       │
│          │   matched element for the current URL)        │
└──────────┴──────────────────────────────────────────────┘
```

A faint brand watermark (`<Watermark />`) sits fixed behind the content on
every role's pages — see §4d.

| Region | Component | What it is |
|--------|-----------|-----------|
| Top bar | `layouts/Navbar.jsx` | Brand icon + "College ERP", sidebar toggle, logout button |
| Sidebar | `layouts/Sidebar.jsx` | User card + role-based menu (from `layouts/sidebarMenu.js`) |
| Page header | built into `Layout.jsx` | Title + breadcrumb, filled by each page via `usePageHeader()` |
| Content slot | `<Outlet />` | **Where each page's unique content renders** |

### The sidebar menu: `frontend/src/layouts/sidebarMenu.js`

`Sidebar.jsx` builds its menu from `menuForUserType(user.user_type)` in this
file. Menu items differ by role (`'1'` admin, `'2'` staff, `'3'` student).

👉 To **add, remove, or rename a sidebar link**, edit this file.

### An individual page: e.g. the admin dashboard

`frontend/src/pages/admin/AdminDashboard.jsx` is a normal React component. It
calls `usePageHeader({ title, breadcrumb })` once (fills the shared header),
fetches its data via `useApi(() => dashboardAPI.adminHome())`, and returns its
own JSX — cards, charts, whatever the page needs. It does **not** repeat the
navbar/sidebar; those come from `Layout.jsx` automatically because the route is
nested under the protected layout route in `App.jsx`.

> **Every logged-in route in `App.jsx` renders inside `Layout`.** That's why a
> change to `Layout.jsx` or to `erpnext-style.css` instantly affects every page.

---

## 4. Where styling actually comes from

### 4a. Load order (`frontend/src/main.jsx`)

```js
import 'bootstrap/dist/css/bootstrap.min.css'
import 'bootstrap/dist/js/bootstrap.bundle.min.js'
import './assets/fontawesome-free/css/all.min.css'
import './assets/css/erpnext-style.css'   // ★ loads LAST, on purpose
```

`erpnext-style.css` loads **after** Bootstrap deliberately: several of our
class names (`.nav-link`, `.btn-outline-primary`, `.card-title`, `.badge`, …)
happen to match real Bootstrap component classes. When two rules tie on CSS
specificity, the one that loads **last** wins — so our theme needs to load
after Bootstrap to reliably override it. (A few rules also use `.erpnext-sidebar
.nav-link` scoping or `!important` as extra insurance — don't remove those
without checking the cascade still wins.)

Chart.js is not a `<script>` tag at all — it's an npm package (`chart.js`)
imported directly in `components/ThemedChart.jsx`.

### 4b. The control panel: CSS variables (`:root`)

At the very top of `erpnext-style.css` is a `:root` block — the **Darbha Prana
Tech Global brand palette** (Deep Teal / Verdant / Antique Gold / Ivory).
Change a value here and it updates everywhere that uses it:

```css
:root {
  --primary-color: #0e4e4c;   /* Deep Teal — sidebar, buttons, links, headings */
  --primary-mid:   #166460;   /* Verdant — gradients, hover states */
  --primary-dark:  #093735;   /* darkest teal — active/pressed states */
  --accent-color:  #c0a054;   /* Antique Gold — highlights, warnings, CTAs */
  --accent-light:  #d8be7e;   /* Light Gold */
  --light-color:   #f5f2e8;   /* Ivory — page background */
  --dark-color:    #23302e;   /* main text color */
  --border-color:  #e1dac8;   /* card / table borders (warm, not cold gray) */
  --text-muted:    #74807c;
  --font-display:  "Cinzel", Georgia, serif;   /* headings, brand name */
  --font-support:  "Jost", -apple-system, sans-serif; /* subtitles, nav labels */
  --sidebar-width: 240px;
  --navbar-height: 60px;
}
```

**Example — nudge the accent color:** change `--accent-color` — the sidebar's
active-menu highlight, warning badges/buttons, and login accents all follow.

The two brand fonts (Cinzel + Jost) are loaded from Google Fonts via a
`<link>` in `frontend/index.html`, not bundled — the app needs network access
on first load to fetch them (they're cached by the browser after that).

### 4c. Two copies of this stylesheet exist — keep them in sync

`main_app/static/dist/css/erpnext-style.css` is a **duplicate**, used only by
the handful of Django-rendered password-reset pages
(`main_app/templates/registration/*.html`, which `{% extends
"registration/erpnext_base.html" %}`). React can't reach those pages (they're
outside the SPA), so they need their own copy of the same CSS file.

> ⚠️ **If you change the brand palette or theme, copy the file again:**
> ```bash
> cp frontend/src/assets/css/erpnext-style.css main_app/static/dist/css/erpnext-style.css
> ```
> There's no build step tying these together — it's a manual sync. Forgetting
> it means the password-reset pages drift out of sync with the rest of the app
> (this happened once already after the original React migration, when the
> brand was refreshed but this copy was missed).

### 4d. Brand assets & the watermark

`frontend/src/assets/image/` holds the brand artwork, extracted from the
Darbha Prana Tech Global logo sheet:

| File | Used by | What it is |
|---|---|---|
| `brand-mark.png` | `layouts/Watermark.jsx` | Monochrome teal grass+arrow mark, alpha-only (background removed) |
| `brand-icon.png` | `layouts/Navbar.jsx`, `pages/Login.jsx` | Full-color two-tone version, small brand icon |
| `brand-app-icon.png` | source for `frontend/public/favicon1.ico` | The teal rounded-square app icon |

`Watermark.jsx` renders `brand-mark.png` as a `position: fixed`, very-low-
opacity (`.brand-watermark` in the CSS), `pointer-events: none` image behind
the content area — on every role's pages via `Layout.jsx`, and centered behind
the login card via `pages/Login.jsx`. It's purely decorative; don't wire data
or interaction to it.

> The app previously had animated Vanta.js (WebGL) backgrounds per role
> (waves/globe/birds). They were **removed** — the production build's module
> bundling made Vanta's UMD exports non-callable, which crashed the whole React
> tree on every login and dashboard load (React unmounts the entire app on an
> uncaught render error with no error boundary present). The static watermark
> replaces them with zero runtime risk.

### 4e. Section map of `erpnext-style.css`

| Want to change… | Look for this comment section |
|---|---|
| Root color/font variables | `:root` at the very top |
| Page background, base fonts | `/* Reset and base styles */` |
| Top bar | `/* Header/Navbar */` |
| Left menu (now a solid teal panel) | `/* Sidebar */`, `/* Navigation Menu */`, `/* Submenu */` |
| Content area width/padding | `/* Main Content */` |
| Page title + breadcrumb | `/* Page Header */` |
| Card panels | `/* Cards */` |
| Dashboard number tiles | `/* Stats Cards */` |
| Buttons | `/* Buttons - ERPNext Style */` |
| Form inputs | `/* Forms */` |
| Tables | `/* Tables */` |
| Alert/notification banners | `/* Alerts */` |
| Brand watermark | `/* Brand watermark */` |
| Login screen | `/* Login Page */` |
| Mobile / tablet behavior | `/* Responsive Design */`, `/* Mobile responsive... */` |
| Dark mode | `/* Dark Mode Styles */` and every `/* Dark mode support... */` |
| Badges | `/* Badge styles for light mode */`, `/* Dark mode badge styles */` |

> 🌓 **Dark mode:** toggled by `#theme-switch` in the navbar (state saved in
> `localStorage`, applied via a `dark-mode` class on `<body>`). The **sidebar
> stays the same solid Deep Teal in both modes** — only the navbar/content
> area follow the toggle. If you add a new light-mode color rule, check whether
> it needs a matching `.dark-mode ...` override, or the two modes will look
> inconsistent.

---

## 5. "I want to change X" — quick recipes

| Goal | File to edit | What to do |
|---|---|---|
| Recolor the whole app | `frontend/src/assets/css/erpnext-style.css` → `:root` | Change `--primary-color` / `--accent-color` (then sync the copy, §4c) |
| Make the sidebar wider/narrower | same file → `:root` | Change `--sidebar-width` |
| Restyle buttons | same file → `/* Buttons */` | Edit `.btn`, `.btn-primary`, etc. |
| Restyle cards | same file → `/* Cards */` | Edit `.erpnext-card`, `.card-header` |
| Change the navbar look | same file → `/* Header/Navbar */` | Edit `.erpnext-navbar` rules |
| Swap the logo / watermark / favicon | `frontend/src/assets/image/` | Replace the `brand-*.png` files; regenerate the favicon (see §4d) |
| Change the brand text "College ERP" | `layouts/Navbar.jsx`, `pages/Login.jsx` | Edit the literal text |
| Add / rename / remove a menu item | `layouts/sidebarMenu.js` | Edit the menu array for that role |
| Change layout shared by all pages | `layouts/Layout.jsx` | Edit navbar / header / content wrapper JSX |
| Restyle one specific page only | that page's `.jsx` in `pages/<role>/` | Edit its JSX / add scoped `<style>` if truly one-off |
| Change the login screen | `pages/Login.jsx` + `/* Login Page */` in the CSS | Markup + styles |
| Tweak dark mode colors | same CSS file → `/* Dark Mode Styles */` | Edit the `.dark-mode ...` rules |
| Add a new API-backed page | `frontend/src/api/*.js` (call) + `main_app/api/*.py` (endpoint) + a `pages/` component + a route in `App.jsx` | See §6 |

---

## 6. Which component/endpoint handles which URL

**Frontend routes** are a flat list in `frontend/src/App.jsx` — search that
file for the URL path (they intentionally mirror the old Django URL scheme,
e.g. `/admin/home/`, `/staff/attendance/take/`) to find the page component.

**API endpoints** are listed in `main_app/api/urls.py`, one line per route,
grouped by resource (auth, dashboard, students, staff, academics, attendance,
results, leave, feedback, notifications, books). Each points at a function in
the matching `main_app/api/<name>.py` module. Business rules (validation,
permissions, cascading promotion, attendance locking, etc.) live in those
modules — `forms.py` and `models.py` are shared with the legacy admin site and
still hold the `ModelForm` validation the API reuses.

The three dashboards specifically:

| Role | Route (`App.jsx`) | Component | API call |
|---|---|---|---|
| Admin | `/admin/home/` | `pages/admin/AdminDashboard.jsx` | `dashboardAPI.adminHome()` → `api/dashboard.py: admin_home` |
| Staff | `/staff/home/` | `pages/staff/StaffDashboard.jsx` | `dashboardAPI.staffHome()` → `admin_home`'s sibling `staff_home` |
| Student | `/student/home/` | `pages/student/StudentDashboard.jsx` | `dashboardAPI.studentHome()` → `student_home` |

---

## 7. Legacy / removed tech — what used to be here

The pre-React version of this app was a server-rendered Django site styled
with a customized **AdminLTE** theme, plus jQuery and a pile of its plugins.
All of that was removed once the React frontend covered every page:

- **Deleted entirely:** `main_app/templates/hod_template/`,
  `staff_template/`, `student_template/`, and the `main_app/` template
  folder (layout partials) — replaced by `frontend/src/pages/` and
  `layouts/Layout.jsx`.
- **Deleted entirely:** `hod_views.py`, `staff_views.py`, `student_views.py`,
  `EditResultView.py`, `middleware.py` (`LoginCheckMiddleWare`) — replaced by
  `main_app/api/*.py` (the JSON endpoints do their own permission checks per
  request instead of a global redirect-to-login middleware).
- **Deleted entirely:** ~390 files / 22 MB of unused static assets under
  `main_app/static/plugins/` — Bootstrap (a duplicate; the live pages use
  Bootstrap from npm or CDN instead), Chart.js (old CDN copy; the app now
  imports `chart.js` from npm), jQuery UI, jQuery Validation, jQuery Knob,
  moment.js, daterangepicker, tempusdominus-bootstrap-4, icheck-bootstrap,
  overlayScrollbars, sparklines — plus the AdminLTE CSS/JS bundle itself
  (`dist/css/adminlte.*`, `dist/css/alt/*`, `dist/css/style.css`, `dist/js/`,
  `dist/img/`) and a dead alternate template (`registration/base.html`).
- **Removed:** animated Vanta.js (WebGL) role backgrounds — see §4d for why.
- **Still present, on purpose:** `main_app/static/plugins/jquery/` and
  `plugins/fontawesome-free/` — the surviving password-reset templates
  (§4c) still load jQuery (for a small `form-control` class-adder script) and
  FontAwesome. Don't delete these without also rewriting those two templates.
- **Firebase Cloud Messaging** (push notifications) was never ported to
  React — notifications are stored server-side and shown in-app only
  (`main_app/api/notifications.py`), no service worker, no push permission
  prompt.

If you're ever unsure whether something is still live: for a **page**, check
`frontend/src/App.jsx` for its route; for a **template**, check whether any
Django view still `render()`s it (only `registration/*.html` do, via
`django.contrib.auth.urls`).

---

## 8. Seeing your changes

### Development (two servers, live-reload both)

```bash
# Terminal 1 — Django API (serves /api/v1/, /django-admin/, /accounts/)
.venv/Scripts/python manage.py runserver        # or: source .venv/bin/activate && python manage.py runserver

# Terminal 2 — Vite dev server (serves the React app, proxies /api and /media to Django)
cd frontend
npm run dev
```

Open **`http://localhost:5173/`** (not 8000) and log in. React/CSS edits
hot-reload instantly; no browser refresh needed. `vite.config.js` proxies
`/api` and `/media` to `http://127.0.0.1:8000` so session/CSRF cookies stay
same-origin.

### Production-style (one server, what actually ships)

```bash
cd frontend && npm run build     # writes frontend/dist/ (hashed assets, base /static/)
cd ..
python manage.py collectstatic --noinput   # copies frontend/dist/ + main_app/static/ into static/
python manage.py runserver                 # (or gunicorn) — now serves EVERYTHING on :8000
```

`main_app/views.py: react_app` serves `frontend/dist/index.html` for every
route except `/api/`, `/django-admin/`, `/accounts/`, `/static/`, `/media/`
(see `main_app/urls.py`'s regex). This is the mode to test in before
considering a change "done" — the dev-server proxy setup can mask static-path
mistakes that only show up once `collectstatic` is involved.

> The root-level `static/` folder is `collectstatic`'s output — it's
> git-ignored and gets fully regenerated by the command above. Never hand-edit
> files there; edit the source under `frontend/src/` or `main_app/static/`
> and rerun `collectstatic`.

---

## 9. Cheat sheet — the files that matter most

1. **`frontend/src/assets/css/erpnext-style.css`** — the entire theme. Start at `:root`. Remember §4c's sync copy.
2. **`frontend/src/layouts/Layout.jsx`** — shared navbar/sidebar/page-header frame.
3. **`frontend/src/layouts/sidebarMenu.js`** — the menu links, per role.
4. **`frontend/src/pages/Login.jsx`** — the login screen.
5. **`frontend/src/App.jsx`** — the full route table (page URLs → components).
6. **`frontend/src/pages/<role>/*.jsx`** — individual page content.
7. **`main_app/api/urls.py`** — the full API route table.

Everything else is data, configuration, or (per §7) removed legacy.

---
---

# Part 2 — Application Features & Domain Logic

> This part documents the **functional features** built on top of the base app
> (the architecture/styling guide above is Part 1). It is the source of truth
> for *how the academic/promotion/attendance/notification logic works and
> where it lives*, so work can continue without prior chat context.
>
> The business logic described below hasn't changed since the React
> migration — it moved from `hod_views.py`/`staff_views.py`/`student_views.py`
> into `main_app/api/*.py` (one call per old view, same rules, same edge
> cases), and from Django forms rendered as HTML into the same `forms.py`
> `ModelForm`s now validating JSON request bodies instead.

## 10. Academic data model (key fields added)

All models are in `main_app/models.py`. Migrations `0014`–`0018` added the fields below.

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
- **`Attendance`**: `session`, `subject`, **`course`** + **`semester`** (nullable,
  migration `0018` — needed because a subject shared across courses can also share a
  session, so course+semester is what actually identifies a class; see §15), `shift`,
  `date`, **`locked`** (bool, migration `0015`).
  **`AttendanceReport`**: `student`, `attendance`, `status`,
  `late`. NOTE: `AttendanceReport.student` is `on_delete=DO_NOTHING` (matters when
  deleting students — delete AttendanceReport rows first).
- **Shift**: `SHIFT_CHOICES = (("morning","Morning Shift"),("day","Day Shift"))`.
  `Staff.teaches_morning` / `teaches_day` booleans; `staff.shifts` / `shifts_display`.

## 11. Course abbreviations (used everywhere except Manage Courses)

Goal: long course names congested tables/banners, so the **abbreviation is shown
everywhere**, with the full name kept in a `title="..."` hover tooltip. The **only**
place that shows the full name + abbr is the **Manage Courses list page**
(`ManageCourses.jsx`, uses `course.name_with_abbr`).

- Pages use `course.short_name` (cards, tables, attendance dropdowns, banners) —
  the API's `serializers.course_dict()` always includes both `short_name` and
  `name_with_abbr` so pages can pick whichever they need.
- Abbreviation is an editable field on **Add/Edit Course** (`CourseForm`, fields
  `['name','abbreviation','semesters']`; used by `main_app/api/academics.py: course_list/course_item`).
- Current values: **BE-IT**, **BE Civil**, **BE Software**.

## 12. Manage Students navigation + cascade promotion

**Nav flow (admin):** `ManageStudents` → `StudentSemesters` (semester tiles)
→ `StudentShifts` (shift tiles) → `StudentList` (student table). Backed by
`main_app/api/students.py`: `manage_courses`, `manage_semesters`, `manage_shifts`,
and `student_list` (filtered by `course`/`semester`/`shift` query params). All
active-student queries filter **`passed_out=False`**.

**Cascade promotion** (`students.py: promote_class` view + helper
`_cascade_promote_course(course, from_semester)` in the same module):
- Promoting semester **N** advances **every semester ≥ N** in that course (both
  shifts) up by one via `update(current_semester=F('current_semester')+1)`, so a
  lower batch never mixes into the batch above it.
- Students at the **final semester** (`course.semesters`) are **not** moved up —
  they are marked `passed_out=True, passed_out_date=today` (graduated).
- The semester-tile page shows **one button per populated semester**: "Promote
  Sem N & above" (non-final) or "Pass out Sem N" (final). Empty semesters show
  "Semester currently not active".

## 13. Passed-out students

- `passed_out` students are **excluded from all active queries** (manage-student
  counts/lists, attendance cohort/`class_students`, dashboard totals — everywhere via
  `passed_out=False`). Their `AttendanceReport` history is kept intact.
- **Passed Out Students** section (sidebar item under Manage Students):
  `PassedOutCourses` → `PassedOutSessions` → `PassedOutStudentList` React pages,
  backed by `students.py: passed_out_courses / passed_out_sessions / passed_out_list`.
  The student table shows **both shifts together** (no shift split), ordered
  alphabetically.

## 14. New-session intake auto-promotion (`student_list` POST)

When a first-year student is added (`main_app/api/students.py: student_list`,
POST, `current_semester==1`) for a session that is **new to that course** AND
the course already has students of an **older** session, the whole course is
**cascade-promoted first** (`_cascade_promote_course(course, 1)`) so the new
intake starts in an empty Sem 1. Conditions (all required):
- `not already_this_session` (no active student of this course already has this session), and
- `older_exists` (`Student.objects.filter(course=course, passed_out=False, session__start_year__lt=session.start_year)`).

This means only the **first** student of a new intake triggers it; older-session
backfills never promote. (It is keyed off the **session being new+newer**, NOT off
Sem 1 being occupied — an earlier version checked Sem-1 occupancy and silently
skipped promotion once Sem 1 had been vacated.)

**Sem-1 closed after a batch progresses** (also `student_list` POST): once a
`(course, session)` batch has moved past Semester 1, that session's Semester 1 is
**closed** — a new student of that session can no longer be added at Sem 1; they
must join the batch at its **current** semester. Rule: if `new_sem == 1` and
`Student.objects.filter(course, session, passed_out=False)` exists but has **none**
at `current_semester=1`, the add is **rejected** with a 400 + error naming the
batch's current semester. Sem 1 stays open while the batch is still running in
Sem 1, and a brand-new session still starts at Sem 1 (handled by the intake
auto-promotion above).

## 15. Staff attendance — Take / Update / View (`main_app/api/attendance.py`)

Shared picker built by `picker_context(staff)`. Picker order:
**Shift → Subject (buttons, filtered by shift) → Class**. `StaffTakeAttendance.jsx`
/ `StaffUpdateAttendance.jsx` / `StaffViewAttendance.jsx` all share
`ClassPicker.jsx` for this UI. Each subject carries a `classes` list (the
concrete classes the teacher teaches it in: `{course, course_name, semester,
shift, active}`); picking a subject+shift filters the Class dropdown to
matching entries. The chosen class resolves to `{course, semester}`, which the
page sends alongside `subject`/`shift` — so the API params (`subject, course,
semester, shift`) are exactly what the old Django view expected.

- **Why course+semester live on `Attendance`** (migration `0018`): a Subject is
  shared across courses at different semesters (via `CourseSubject`), and two such
  classes can share the **same intake `Session`** (e.g. Computer Network = BE-IT
  Sem 6 **and** BE Software Sem 5, both session 2022). Identifying a class only by
  `session` (+subject+shift) would return the **wrong cohort**. `Attendance` stores
  **`course`** + **`semester`** (both nullable; back-filled for existing rows in
  `0018`), and the API filters by `subject + shift + course + semester` exactly.
- **Active classes only** (`active` flag): a class is *active* when a current cohort
  sits at that `(course, current_semester, shift)`. The frontend honours a
  `restrictActive` prop on `ClassPicker` — **`true` on Take/Update** (inactive/not-
  running semesters are hidden), **`false` on View** (history of inactive classes
  stays viewable, labelled "(inactive)").
- **Take Attendance** (`attendance.py: attendance_list` POST /
  `class_students` GET): `class_students` filters by course + **`current_semester`**
  + shift + `passed_out=False` (so promoted students don't show for a lower-semester
  subject). **No status is preselected** in the UI; the page blocks saving until
  every student is marked. Saving stores `course`+`semester`, **derives
  `Attendance.session`** from the cohort's `Student.session` (returns `NO_SESSION`
  if unset — as a `{code: "NO_SESSION"}` 400), and validates the teacher is assigned
  for that course/semester/shift (else `{code: "NOT_ASSIGNED"}`).
- **Update Attendance** (`attendance_update` PUT): saving an update **locks** the
  record (`Attendance.locked=True`); it then can't be edited again (`{code:
  "LOCKED"}` 400 on a second attempt). The list endpoint only returns **unlocked**
  records by default here. The `NOT_ASSIGNED` check validates against the record's
  **own** `course`+`semester`+`shift`.
- **View Attendance** (`StaffViewAttendance.jsx`, read-only): same picker; shows
  status as colored badges. Calls the attendance-list endpoint with
  `include_locked=1` to show **all** dates (locked ones labelled "— confirmed").
- Fetched/displayed students show **roll number** (not registration), name as
  **"First Last"**, ordered alphabetically by first then last name.

## 16. Notify Student / Notify Staff (`main_app/api/notifications.py`)

- **Notify Staff**: names shown "First Last", ordered alphabetically.
- **Notify Student**: mirrors Manage Students — the landing page
  (`NotifyStudent.jsx` / `notifications.py: student_browse`) has a **global
  student search** (across all active students) **plus** course tiles →
  semester tiles → student list (both shifts together). Course shown as
  abbreviation; names "First Last", alphabetical; passed-out excluded. Sending
  a notification stores it server-side (`NotificationStaff`/`NotificationStudent`
  models) for the recipient's "View Notifications" page — no push/FCM.

## 17. Migrations added (in order)

| Migration | Adds |
|---|---|
| `0014_student_current_semester` | `Student.current_semester` |
| `0015_attendance_locked` | `Attendance.locked` |
| `0016_auto_20260625_2320` | `Student.passed_out`, `Student.passed_out_date` |
| `0017_course_abbreviation` | `Course.abbreviation` |
| `0018_auto_20260627_1452` | `Attendance.course`, `Attendance.semester` (+ data backfill) |

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

- **Run app / one-off scripts:** activate `.venv` first
  (`.venv/Scripts/python` on Windows, `source .venv/bin/activate` elsewhere).
  Django is **3.1.1** (pinned, old — keep code compatible with it) on a
  **Python 3.14** interpreter, which needs two compat shims not in Django's own
  requirements: `setuptools` (provides `distutils`, removed from the stdlib in
  3.12) and `legacy-cgi` (provides the `cgi` module, removed in 3.13) — both are
  pinned in `requirements.txt`. Standalone scripts need
  `sys.path.insert(0, "<project root>")` before `django.setup()`.
  `python manage.py runserver` (auto-reloads on Python edits; **not** on frontend
  edits — see §8 for the two-server dev setup).
- **Bulk DB changes:** back up first — `cp db.sqlite3 db.sqlite3.bak-<reason>-<ts>`.
  Wrap mutations in `transaction.atomic()`. To **verify behavior without
  committing**, run inside `with transaction.atomic(): ... raise <Rollback>` and
  catch it (used throughout to test promotion/intake/API endpoints against the
  live DB safely — see e.g. the smoke-test pattern used when the API layer was built).
- **Deleting students:** delete `AttendanceReport` first (it's `DO_NOTHING`), then
  `CustomUser.objects.filter(user_type='3').delete()` (cascades Student + children).
- **Seeding speed:** hash the shared password **once**
  (`make_password(...)`) and reuse the string — per-user hashing is the bottleneck.
  Ensure any `unique_*` helper actually increments (a missing `n += 1` caused an
  infinite loop once).

## 20. Repo, environment & cross-device workflow

How the project is packaged and moved between machines.

- **Python version:** **3.14**, via a local `.venv` (see §19 for the two compat
  shims this requires with Django 3.1.1). Deps are pinned in
  `requirements.txt`; setup is `python -m venv .venv` → activate it →
  `pip install -r requirements.txt` → `python manage.py runserver`. The
  frontend needs Node/npm separately: `cd frontend && npm install`.
- **The database is committed.** `db.sqlite3` is **intentionally tracked in git**
  (the `.gitignore` says so) so data + the admin login travel between devices. No
  `migrate`/seed step is needed on a fresh clone — the data is already there.
  - ⚠️ **Consequence:** don't edit on two devices at once. Finish on one →
    `git push` → `git pull` on the other before continuing, or the DB conflicts.
  - **Backups** (`db.sqlite3.bak*`), `.venv/`, `frontend/node_modules/`, and
    `frontend/dist/` are git-ignored, as is the root-level `static/`
    (`collectstatic` output).
- **Secrets in the repo:** `SECRET_KEY` and a Google reCAPTCHA key live in the
  code, so the **repository must stay private**.
- **`README.md`** is the onboarding doc (clone → install → run, login
  credentials, and the git workflow). This file (`STYLING_ARCHITECTURE.md`) is
  the deep reference it links to.
- **Deployment:** no hosted deployment is currently configured — the project
  runs locally and is shared between devices via git with the SQLite DB
  committed (see above). `gunicorn`/`whitenoise` remain in `requirements.txt`
  for when that changes; `whitenoise` is also what serves the built frontend's
  static assets in the single-server production-style setup (§8).
