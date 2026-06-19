import ipaddress
import json
import socket
from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import httpx
import magic
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from PIL import Image, UnidentifiedImageError


class RecipeJSONParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.capture = False
        self.parts = []
        self.documents = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script" and attrs.get("type", "").lower() == "application/ld+json":
            self.capture = True
            self.parts = []

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag == "script" and self.capture:
            self.capture = False
            try:
                self.documents.append(json.loads("".join(self.parts)))
            except json.JSONDecodeError:
                pass


def validate_public_url(url):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username or parsed.password:
        raise ValidationError("Unsupported URL.")
    if parsed.port not in {None, 80, 443}:
        raise ValidationError("Unsupported port.")
    try:
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, parsed.port or 443)}
    except socket.gaierror as error:
        raise ValidationError("Host cannot be resolved.") from error
    for value in addresses:
        address = ipaddress.ip_address(value)
        if not address.is_global:
            raise ValidationError("Private and special network destinations are blocked.")
    return parsed


def import_from_url(url):
    for _ in range(4):
        parsed = validate_public_url(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        robot = RobotFileParser(robots_url)
        try:
            robot.read()
            if not robot.can_fetch("MealHouseRecipeImporter/1.0", url):
                raise ValidationError("The site does not permit automated recipe import.")
        except OSError as error:
            raise ValidationError("Unable to verify robots.txt.") from error
        response = httpx.get(
            url,
            headers={"User-Agent": "MealHouseRecipeImporter/1.0 (+https://codex-shitshow.fejlgoblin.ovh)"},
            follow_redirects=False,
            timeout=10,
        )
        if response.status_code in {301, 302, 303, 307, 308}:
            url = urljoin(url, response.headers["location"])
            continue
        response.raise_for_status()
        if len(response.content) > 2_000_000:
            raise ValidationError("Response is too large.")
        if "text/html" not in response.headers.get("content-type", ""):
            raise ValidationError("URL did not return HTML.")
        parser = RecipeJSONParser()
        parser.feed(response.text)
        for document in parser.documents:
            candidates = document if isinstance(document, list) else document.get("@graph", [document]) if isinstance(document, dict) else []
            for candidate in candidates:
                if isinstance(candidate, dict) and "Recipe" in ([candidate.get("@type")] if isinstance(candidate.get("@type"), str) else candidate.get("@type", [])):
                    return candidate
        raise ValidationError("No Schema.org Recipe data was found.")
    raise ValidationError("Too many redirects.")


def normalize_import(payload):
    data = json.loads(payload) if isinstance(payload, str) else payload
    if not isinstance(data, dict):
        raise ValidationError("Recipe data must be an object.")
    return {
        "name": str(data.get("name", ""))[:200],
        "description": str(data.get("description", ""))[:5000],
        "servings": _parse_servings(data.get("recipeYield", data.get("servings", 4))),
        "instructions": _parse_instructions(data.get("recipeInstructions", data.get("instructions", []))),
        "ingredients": data.get("recipeIngredient", data.get("ingredients", [])),
        "source_url": str(data.get("url", ""))[:500],
    }


def _parse_servings(value):
    import re
    match = re.search(r"\d+(?:[.,]\d+)?", str(value))
    return match.group(0).replace(",", ".") if match else "4"


def _parse_instructions(value):
    if isinstance(value, str):
        return [value]
    result = []
    for item in value or []:
        result.append(str(item.get("text", "")) if isinstance(item, dict) else str(item))
    return [item[:5000] for item in result if item]


def sanitize_raster_upload(upload):
    if upload.size > settings.MAX_IMAGE_BYTES:
        raise ValidationError("Image is too large.")
    header = upload.read(4096)
    upload.seek(0)
    mime = magic.from_buffer(header, mime=True)
    if mime not in {"image/jpeg", "image/png", "image/webp"}:
        raise ValidationError("Only JPEG, PNG, and WebP images are accepted.")
    try:
        image = Image.open(upload)
        image.verify()
        upload.seek(0)
        image = Image.open(upload)
        image.thumbnail((2400, 2400))
        if image.mode not in {"RGB", "L"}:
            background = Image.new("RGB", image.size, "white")
            if image.mode == "RGBA":
                background.paste(image, mask=image.getchannel("A"))
            else:
                background.paste(image.convert("RGB"))
            image = background
        elif image.mode == "L":
            image = image.convert("RGB")
        from io import BytesIO
        output = BytesIO()
        image.save(output, format="JPEG", quality=88, optimize=True)
        return ContentFile(output.getvalue(), name="upload.jpg")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValidationError("Invalid image file.") from error
