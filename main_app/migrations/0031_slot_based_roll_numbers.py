"""Rewrite roll numbers from YY-C-S-NN to YY-SS-NN.

Digits 3-4 stop being "course code, then shift digit" and become a single
two-digit slot allocated one per (course, shift) pair — course 1 owns 01
morning and 02 day, course 2 owns 03 and 04, and so on. The one-digit course
code capped the college at ten courses; 99 slots carries 49.

Only the middle two digits move. The intake year in front and the alphabetical
position behind are carried across untouched, so a locked intake keeps every
position exactly as issued.
"""
from django.db import migrations

SHIFT_OFFSET = {"morning": 0, "day": 1}


def forwards(apps, schema_editor):
    Student = apps.get_model('main_app', 'Student')
    seen = {}
    clashes = []
    for student in Student.objects.select_related(
            'session', 'course').order_by('id'):
        if not student.roll_number or len(student.roll_number) != 6:
            continue
        session, course = student.session, student.course
        if session is None or not session.start_year or not course or not course.code:
            continue
        offset = SHIFT_OFFSET.get(student.shift)
        if offset is None:
            continue
        slot = (course.code - 1) * 2 + 1 + offset
        if slot > 99:
            raise RuntimeError(
                "Course %r has code %d, which needs roll-number slot %d — past "
                "the two digits available. Renumber the courses to 1-49 first."
                % (course.name, course.code, slot))
        rebuilt = "%02d%02d%s" % (
            session.start_year.year % 100, slot, student.roll_number[-2:])
        if rebuilt in seen:
            clashes.append((rebuilt, seen[rebuilt], student.pk))
            continue
        seen[rebuilt] = student.pk
        student.roll_number = rebuilt
        student.save(update_fields=['roll_number'])

    if clashes:
        raise RuntimeError(
            "Rebuilding slots collided on %d roll number(s): %s. Reassign "
            "those students' roll numbers manually, then re-run."
            % (len(clashes), ", ".join(
                "%s (students %s and %s)" % c for c in clashes)))


def backwards(apps, schema_editor):
    """Not reversible — the slot cannot be split back into a one-digit course
    code once codes past 9 exist."""


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0030_course_code_as_slot_ordinal'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
