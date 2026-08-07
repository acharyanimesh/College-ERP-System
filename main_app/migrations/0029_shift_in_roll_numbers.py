"""Move roll numbers from YY-CC-NN to YY-C-S-NN, adding the shift digit.

Course codes shrink to one digit, and digit 4 becomes the shift (0 morning,
1 day) so the two shifts of an intake are numbered independently.

Existing students keep their alphabetical POSITION — only the prefix in front
of it is rewritten. Renumbering them from scratch would be wrong twice over:
positions were shared across both shifts under the old scheme, and any intake
already locked is locked precisely because its numbers must not move. Splitting
a mixed-shift intake here would therefore leave collisions the old scheme never
had, which the final pass detects and reports rather than silently papering
over.
"""
from django.db import migrations


def to_single_digit_codes(apps, schema_editor):
    """11 -> 1, 12 -> 2 ... keeping the digit the admin already recognises,
    and falling back to the next free digit when that one is taken."""
    Course = apps.get_model('main_app', 'Course')
    taken = set()
    pending = []
    for course in Course.objects.order_by('id'):
        wanted = (course.code or '')[-1:]
        if wanted and wanted not in taken:
            taken.add(wanted)
            course.code = wanted
            course.save(update_fields=['code'])
        else:
            pending.append(course)
    for course in pending:
        for candidate in "1234567890":
            if candidate not in taken:
                taken.add(candidate)
                course.code = candidate
                course.save(update_fields=['code'])
                break
        else:
            raise RuntimeError(
                "More than ten courses exist, so they cannot all have a "
                "single-digit course code. Merge or remove one first.")


def rewrite_roll_numbers(apps, schema_editor):
    Student = apps.get_model('main_app', 'Student')
    shift_digits = {"morning": "0", "day": "1"}
    seen = {}
    clashes = []
    for student in Student.objects.select_related(
            'session', 'course').order_by('id'):
        if not student.roll_number or len(student.roll_number) != 6:
            continue
        session, course = student.session, student.course
        if session is None or not session.start_year or not course or not course.code:
            continue
        digit = shift_digits.get(student.shift)
        if digit is None:
            continue
        # Last two digits are the alphabetical position; carry them across.
        rebuilt = "%02d%s%s%s" % (
            session.start_year.year % 100, course.code, digit,
            student.roll_number[-2:])
        if rebuilt in seen:
            clashes.append((rebuilt, seen[rebuilt], student.pk))
            continue
        seen[rebuilt] = student.pk
        student.roll_number = rebuilt
        student.save(update_fields=['roll_number'])

    if clashes:
        raise RuntimeError(
            "Splitting shifts collided on %d roll number(s): %s. These intakes "
            "held both shifts under one alphabetical run, so the positions "
            "cannot be carried across as-is. Reassign the affected students' "
            "roll numbers manually, then re-run this migration."
            % (len(clashes), ", ".join(
                "%s (students %s and %s)" % c for c in clashes)))


def forwards(apps, schema_editor):
    to_single_digit_codes(apps, schema_editor)
    rewrite_roll_numbers(apps, schema_editor)


def backwards(apps, schema_editor):
    """Not reversible — the old two-digit codes are not recoverable from the
    single digit, and 0028 restores the column width anyway."""


class Migration(migrations.Migration):

    dependencies = [
        ('main_app', '0028_single_digit_course_code'),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
