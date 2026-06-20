import hashlib
from urllib.parse import urlparse

import httpx
from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render

from operations.services import enqueue

from .forms import ManualOfferImportForm
from .models import GroceryOffer, OfferProvider, ProductIngredientMatch
from .services import import_manual_records


@login_required
def offer_list(request):
    offers = GroceryOffer.objects.filter(is_active=True).select_related("store", "product")
    query = request.GET.get("q", "").strip()[:100]
    chain = request.GET.get("chain", "").strip()[:150]
    if query:
        offers = offers.filter(
            Q(product_name__icontains=query)
            | Q(brand__icontains=query)
            | Q(category__icontains=query)
        )
    if chain:
        offers = offers.filter(store__chain=chain)
    offers = offers.order_by("ends_at", "offer_price")
    page = Paginator(offers, 48).get_page(request.GET.get("page"))
    chains = (
        GroceryOffer.objects.filter(is_active=True)
        .exclude(store__chain="")
        .values_list("store__chain", flat=True)
        .distinct()
        .order_by("store__chain")
    )
    return render(
        request,
        "offers/list.html",
        {"offers": page.object_list, "page": page, "query": query, "chain": chain, "chains": chains},
    )


@login_required
def image_proxy(request):
    url = request.GET.get("url", "")
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or parsed.hostname not in settings.SALLING_GROUP_IMAGE_HOSTS
        or parsed.username
        or parsed.password
        or parsed.port not in (None, 443)
    ):
        raise Http404
    key = f"offer-image:{hashlib.sha256(url.encode()).hexdigest()}"
    cached = cache.get(key)
    if cached is None:
        try:
            response = httpx.get(
                url,
                follow_redirects=False,
                timeout=settings.SALLING_GROUP_REQUEST_TIMEOUT_MS / 1000,
                headers={"User-Agent": "MealHouse/1.0"},
            )
            response.raise_for_status()
        except (httpx.HTTPError, ValueError) as error:
            raise Http404 from error
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        if content_type not in {"image/jpeg", "image/png", "image/webp"} or len(response.content) > 2_000_000:
            raise Http404
        cached = (response.content, content_type)
        cache.set(key, cached, 3600)
    body, content_type = cached
    result = HttpResponse(body, content_type=content_type)
    result["Cache-Control"] = "private, max-age=3600"
    result["X-Content-Type-Options"] = "nosniff"
    return result


@staff_member_required
def provider_admin(request):
    return render(request, "offers/providers.html", {
        "providers": OfferProvider.objects.all(),
        "matches": ProductIngredientMatch.objects.filter(approved=False).select_related("product", "ingredient")[:100],
    })


@staff_member_required
def synchronize(request, provider_id):
    if request.method == "POST":
        enqueue("offers.sync", {"provider_id": str(provider_id)}, dedupe_key=None)
    return redirect("offers:providers")


@staff_member_required
def manual_import(request):
    form = ManualOfferImportForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        records = form.cleaned_data["payload"]
        if not isinstance(records, list):
            form.add_error("payload", "Expected a JSON array.")
        else:
            provider, _ = OfferProvider.objects.get_or_create(
                name="Administrator manual imports",
                kind=OfferProvider.Kind.MANUAL,
                defaults={"enabled": True, "attribution": "Administrator-supplied data"},
            )
            if request.POST.get("confirm") == "yes":
                import_manual_records(provider, records)
                return redirect("offers:list")
            request.session["manual_offer_preview"] = records[:100]
    return render(request, "offers/import.html", {"form": form})
