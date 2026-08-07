"""Seed the counters the new generated identifiers are derived from, and
reissue the identifiers themselves for rows created before they existed.

Registration numbers change shape here (XXXX-XXXX-XXXX becomes
YYYY-XX-XX-XXXX), so every pre-existing student is renumbered rather than
migrated in place — there is no way to read an old free-typed number as the
new structured one.
"""
from django.db import migrations


def seed(apps, schema_editor):
    Course = apps.get_model('main_app', 'Course')
    Session = apps.get_model('main_app', 'Session')
    Staff = apps.get_model('main_app', 'Staff')
    Student = apps.get_model('main_app', 'Student')

    # Course codes: the two digits that sit in the middle of a roll number.
    # Seeded in creation order from 11; the admin can change any of them on the
    # Edit Course page, since only future roll numbers read this field.
    next_code = 11
    for course in Course.objects.order_by('id'):
        if not course.code:
            course.code = "%02d" % next_code
            course.save(update_fields=['code'])
            next_code += 1

    # Batch codes: the third group of a registration number, counting intakes
    # college-wide. Existing sessions are numbered oldest-first so that the
    # numbers issued from here match the order the intakes actually happened.
    next_batch = 1
    for session in Session.objects.order_by('start_year', 'id'):
        if session.batch_code is None:
            session.batch_code = next_batch
            session.save(update_fields=['batch_code'])
            next_batch += 1

    # Staff IDs, keyed to the year the account was created.
    per_year = {}
    for staff in Staff.objects.select_related('admin').order_by('id'):
        if staff.staff_id:
            continue
        year = staff.admin.created_at.year if staff.admin.created_at else 2025
        serial = per_year.get(year, 0) + 1
        per_year[year] = serial
        staff.staff_id = "%02d%04d" % (year % 100, serial)
        staff.save(update_fields=['staff_id'])

    # Students: registration numbers run per session, roll numbers run per
    # (session, course) in alphabetical order — the same rules idgen applies
    # from now on, just replayed over the rows that are already here.
    reg_serial = {}
    for student in Student.objects.select_related(
            'admin', 'session', 'course').order_by('id'):
        session = student.session
        if session is None or not session.start_year:
            continue
        serial = reg_serial.get(session.id, 0) + 1
        reg_serial[session.id] = serial
        student.registration_number = "%04d-01-%02d-%04d" % (
            session.start_year.year, session.batch_code, serial)
        student.save(update_fields=['registration_number'])

    cohorts = {}
    for student in Student.objects.select_related(
            'admin', 'session', 'course').order_by('id'):
        if student.session_id is None or student.course_id is None:
            continue
        cohorts.setdefault(
            (student.session_id, student.course_id), []).append(student)
    for (session_id, course_id), members in cohorts.items():
        session = Session.objects.get(id=session_id)
        course = Course.objects.get(id=course_id)
        if not session.start_year or not course.code:
            continue
        prefix = "%02d%s" % (session.start_year.year % 100, course.code)
        members.sort(key=lambda s: (
            (s.admin.last_name or "").strip().lower(),
            (s.admin.first_name or "").strip().lower(),
            (s.admin.middle_name or "").strip().lower(),
            s.pk))
        for position, student in enumerate(members[:99], 1):
            student.roll_number = "%s%02d" % (prefix, position)
            student.save(update_fields=['roll_number'])


def unseed(apps, schema_editor):
    """Nothing to undo — 0025 drops the columns these values live in."""


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0025_generated_identifiers'),
    ]

    operations = [
        migrations.RunPython(seed, unseed),
    ]
