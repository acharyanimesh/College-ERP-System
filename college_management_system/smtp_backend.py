"""SMTP email backend compatible with Python 3.12+.

Django 3.1's smtp.EmailBackend.open() calls smtplib's starttls() with the
keyfile/certfile arguments that Python 3.12 removed, so sending mail crashes
with `TypeError: SMTP.starttls() got an unexpected keyword argument
'keyfile'` on this project's Python 3.14 venv. This subclass reimplements
open() using the modern ssl-context API; everything else (send_messages,
settings wiring) is inherited unchanged.
"""
import ssl

from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend
from django.core.mail.utils import DNS_NAME


class EmailBackend(DjangoSMTPBackend):
    def open(self):
        if self.connection:
            return False
        connection_params = {'local_hostname': DNS_NAME.get_fqdn()}
        if self.timeout is not None:
            connection_params['timeout'] = self.timeout
        if self.use_ssl:
            connection_params['context'] = ssl.create_default_context()
        try:
            self.connection = self.connection_class(
                self.host, self.port, **connection_params)
            if not self.use_ssl and self.use_tls:
                self.connection.starttls(context=ssl.create_default_context())
            if self.username and self.password:
                self.connection.login(self.username, self.password)
            return True
        except OSError:
            if not self.fail_silently:
                raise
