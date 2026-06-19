from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from operations.services import enqueue

from .forms import ManualOfferImportForm
from .models import GroceryOffer, OfferProvider, ProductIngredientMatch
from .services import import_manual_records


@login_required
def offer_list(request):
    offers = GroceryOffer.objects.filter(is_active=True).select_related("store", "product")
    return render(request, "offers/list.html", {"offers": offers[:300]})


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
