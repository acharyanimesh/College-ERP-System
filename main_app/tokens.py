from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailVerificationTokenGenerator(PasswordResetTokenGenerator):
    """Like the password-reset token, but keyed off `is_active`/`email_verified`
    instead of `last_login`/`password` so it invalidates itself the moment
    the thing it's verifying happens (Staff/Student activation flips
    is_active; Admin confirmation flips email_verified) — and never before,
    since both are untouched until then. Serves both flows so one token
    generator (and one link format) covers both."""

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.is_active}{user.email_verified}{timestamp}{user.email}"


email_verification_token = EmailVerificationTokenGenerator()
