import ssl
from functools import cached_property

from django.conf import settings
from django.core.mail.backends.smtp import EmailBackend as DjangoSMTPBackend


class EmailBackend(DjangoSMTPBackend):
    """SMTP backend with a connection-local trust store.

    The configured certificate is trusted only by this backend. Hostname,
    validity period, and certificate-signature verification remain enabled.
    """

    @cached_property
    def ssl_context(self):
        ca_file = settings.SMTP_CA_FILE
        if not ca_file:
            return ssl.create_default_context()
        if self.host != "mail.taxoz.org":
            raise ssl.SSLCertVerificationError(
                "MealHouse SMTP certificate trust is restricted to mail.taxoz.org"
            )
        return ssl.create_default_context(cafile=ca_file)
