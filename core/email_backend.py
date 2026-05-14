import socket
from django.core.mail.backends.smtp import EmailBackend
import logging

logger = logging.getLogger(__name__)

class IPv4EmailBackend(EmailBackend):
    """
    Custom SMTP email backend that forces IPv4.
    Useful on platforms like Render where IPv6 routing to Gmail might be broken.
    """
    def _connect(self):
        # Patch the socket.getaddrinfo to filter for IPv4
        original_getaddrinfo = socket.getaddrinfo

        def ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
            # Force AF_INET (IPv4)
            return original_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)

        socket.getaddrinfo = ipv4_getaddrinfo
        try:
            logger.info(f"Attempting to connect to SMTP host: {self.host}:{self.port} (Forced IPv4)")
            return super()._connect()
        finally:
            # Restore the original getaddrinfo
            socket.getaddrinfo = original_getaddrinfo
