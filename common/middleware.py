import ipaddress
import uuid

from django.conf import settings


class RequestIDMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.request_id = uuid.uuid4().hex
        response = self.get_response(request)
        response["X-Request-ID"] = request.request_id
        return response


class TrustedProxyMiddleware:
    """Honor forwarding headers only from configured proxy networks."""

    def __init__(self, get_response):
        self.get_response = get_response
        self.networks = [ipaddress.ip_network(value) for value in settings.TRUSTED_PROXY_CIDRS]

    def __call__(self, request):
        peer_text = request.META.get("REMOTE_ADDR", "")
        try:
            peer = ipaddress.ip_address(peer_text)
            trusted = any(peer in network for network in self.networks)
        except ValueError:
            trusted = False

        request.client_ip = peer_text
        request.is_trusted_proxy = trusted
        if trusted:
            forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR", "")
            first = forwarded_for.split(",", 1)[0].strip()
            try:
                request.client_ip = str(ipaddress.ip_address(first))
            except ValueError:
                pass
            if request.META.get("HTTP_X_FORWARDED_PROTO", "").split(",", 1)[0].strip() == "https":
                request.META["wsgi.url_scheme"] = "https"
        else:
            for key in (
                "HTTP_X_FORWARDED_FOR",
                "HTTP_X_FORWARDED_HOST",
                "HTTP_X_FORWARDED_PROTO",
                "HTTP_X_REAL_IP",
            ):
                request.META.pop(key, None)
        return self.get_response(request)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response.setdefault(
            "Content-Security-Policy",
            "default-src 'self'; img-src 'self' data:; style-src 'self'; "
            "script-src 'self'; font-src 'self'; connect-src 'self'; "
            "frame-ancestors 'none'; base-uri 'self'; form-action 'self'",
        )
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        response.setdefault("Cross-Origin-Resource-Policy", "same-origin")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        return response

