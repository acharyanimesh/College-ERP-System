"""Create — or repair — the administrator account a deployment starts with.

`createsuperuser` is not enough on a host like Render. It refuses to run a
second time, so it cannot fix an account that has drifted; and the account it
makes has `email_verified = False`, which drops the admin straight into the
"confirm your institutional email" screen on first login. On a deployment
whose SMTP is not configured yet, that mail goes to the console — that is, to
a log file — and the administrator is locked out of their own system by a
link they cannot reach.

So this command treats the environment as the source of truth and makes the
database match it: right email, right password, right role, verified, active,
with the Admin profile the dashboards expect. Running it repeatedly is normal
and is how a forgotten password gets reset — set the variable, redeploy.

It deliberately does not touch any other account.
"""
import os

from django.core.management.base import BaseCommand
from django.db import transaction

from ...models import Admin, CustomUser

EMAIL_VAR = 'DJANGO_SUPERUSER_EMAIL'
PASSWORD_VAR = 'DJANGO_SUPERUSER_PASSWORD'


class Command(BaseCommand):
    help = ("Create or repair the bootstrap administrator from "
            "%s / %s." % (EMAIL_VAR, PASSWORD_VAR))

    def handle(self, *args, **options):
        email = (os.environ.get(EMAIL_VAR) or '').strip().lower()
        password = os.environ.get(PASSWORD_VAR) or ''

        if not email or not password:
            # Not an error: local development and any deploy that has already
            # been set up run this with nothing configured, and should pass
            # straight through without failing the build.
            self.stdout.write(
                "%s / %s not set — skipping admin bootstrap."
                % (EMAIL_VAR, PASSWORD_VAR))
            return

        with transaction.atomic():
            user = CustomUser.objects.filter(email=email).first()
            created = user is None
            if created:
                user = CustomUser(email=email, first_name='College',
                                  last_name='Administrator')
            else:
                # save_user_profile (a post_save receiver) does
                # `instance.admin.save()` for user_type 1 and raises
                # RelatedObjectDoesNotExist when there is no Admin row — the
                # state of any account that was a different role until now.
                # Its sibling receiver only creates profiles for brand new
                # users, so nothing else will do this for us. Must happen
                # BEFORE the save below, not after.
                Admin.objects.get_or_create(admin=user)

            user.user_type = 1          # HOD: the application's own admin role
            user.is_active = True       # ...able to log in at all
            user.is_staff = True        # ...and into /django-admin/
            user.is_superuser = True
            # The point of the whole command. Without this the first login is
            # a verification screen whose email nobody can receive yet.
            user.email_verified = True
            # Any half-finished email change is abandoned here; leaving one
            # set would put the setup screen back in front of them.
            user.pending_email = ''
            user.pending_email_approved = False
            user.set_password(password)
            user.save()

            # Created by post_save for a new user; get_or_create covers the
            # case of an existing account that somehow lost its profile, or
            # was created as a different role before being promoted here.
            _, profile_created = Admin.objects.get_or_create(admin=user)

        self.stdout.write(self.style.SUCCESS(
            "Admin %s: %s (password set from %s, email pre-verified%s)"
            % (email,
               "created" if created else "updated",
               PASSWORD_VAR,
               ", Admin profile created" if profile_created else "")))
