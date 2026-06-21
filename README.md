# College ERP

A Django-based College Management System with role-based dashboards for Admin/HOD,
Staff, and Students — managing courses, subjects, sessions, attendance, leave
requests, feedback, results, and notifications.

## Tech Stack

- **Backend:** Django 3.1
- **Database:** SQLite (default) / MySQL
- **Frontend:** Bootstrap, AdminLTE
- **Server:** Gunicorn + WhiteNoise

## Getting Started

```bash
# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate        # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create an admin user
python manage.py createsuperuser

# Run the development server
python manage.py runserver
```

Then open http://127.0.0.1:8000/ in your browser.

## User Roles

- **Admin / HOD** — manage staff, students, courses, subjects, and sessions
- **Staff** — take attendance, manage results, view/respond to leave & feedback
- **Student** — view attendance and results, apply for leave, submit feedback

## License

Released under the [MIT License](LICENSE).
