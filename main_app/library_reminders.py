"""The "your book is due soon" sweep.

Lives outside the API layer because two callers need it: the
`send_due_reminders` management command (scheduled daily) and the button on
the librarian dashboard. Both go through send_due_soon_reminders() so a
reminder reads the same however it was triggered.
"""
from datetime import date, timedelta

from .models import (DUE_SOON_REMINDER_DAYS, BookRequest, NotificationStudent)


def due_soon_loans(today=None, days_ahead=DUE_SOON_REMINDER_DAYS):
    """Loans landing exactly `days_ahead` days from now that nobody has been
    nudged about yet.

    Exactly, not "within" — a loan due in three days should produce one
    reminder on one day, not a fresh one every morning until it is due. The
    reminder_sent_on guard then makes re-running the same day a no-op, so the
    sweep is safe to fire by hand as often as you like.
    """
    today = today or date.today()
    return BookRequest.objects.filter(
        status=BookRequest.ISSUED,
        due_date=today + timedelta(days=days_ahead),
        reminder_sent_on__isnull=True,
    ).select_related('book', 'student__admin')


def send_due_soon_reminders(today=None):
    """Notify every student whose book is due soon.

    Returns {'sent': int, 'messages': [str]} — the messages are for the
    command's stdout and the dashboard's confirmation toast.
    """
    today = today or date.today()
    sent = []
    for loan in due_soon_loans(today):
        renewal_hint = (
            " You can request a one-week renewal from My Borrowings."
            if loan.can_request_renewal else
            " This loan has already been renewed, so it needs to come back.")
        NotificationStudent.objects.create(
            student=loan.student,
            message="Library: \"%s\" is due on %s (in %d days).%s" % (
                loan.book.name,
                loan.due_date.strftime('%b. %d, %Y'),
                (loan.due_date - today).days,
                renewal_hint))
        loan.reminder_sent_on = today
        loan.save(update_fields=['reminder_sent_on'])
        sent.append("%s — %s (due %s)" % (
            loan.student.admin.first_name or loan.student.admin.email,
            loan.book.name,
            loan.due_date.strftime('%b. %d, %Y')))
    return {'sent': len(sent), 'messages': sent}
