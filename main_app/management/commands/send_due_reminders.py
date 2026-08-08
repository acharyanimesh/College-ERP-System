"""Daily nudge for library books coming due.

Schedule this once a day (Windows Task Scheduler / cron):

    python manage.py send_due_reminders

Safe to run repeatedly — each loan is reminded about once, so a second run on
the same day sends nothing. `--dry-run` shows what would go out without
writing anything.
"""
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from ...library_reminders import due_soon_loans, send_due_soon_reminders


class Command(BaseCommand):
    help = "Notify students whose borrowed books are due in 3 days."

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run', action='store_true',
            help="List the reminders that would be sent, then stop.")
        parser.add_argument(
            '--date', dest='on_date',
            help="Pretend today is this YYYY-MM-DD (for testing).")

    def handle(self, *args, **options):
        today = date.today()
        if options['on_date']:
            try:
                today = datetime.strptime(options['on_date'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError("--date must look like YYYY-MM-DD.")

        if options['dry_run']:
            loans = list(due_soon_loans(today))
            for loan in loans:
                self.stdout.write("  would remind %s — %s (due %s)" % (
                    loan.student, loan.book.name, loan.due_date))
            self.stdout.write(self.style.WARNING(
                "dry run: %d reminder(s) would be sent" % len(loans)))
            return

        result = send_due_soon_reminders(today)
        for line in result['messages']:
            self.stdout.write("  reminded %s" % line)
        self.stdout.write(self.style.SUCCESS(
            "%d reminder(s) sent" % result['sent']))
