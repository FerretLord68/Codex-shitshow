import json

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.services import audit_event
from common.decorators import household_permission

from .forms import RecipeForm, RecipeImageForm, RecipeImportForm, RecipeIngredientForm
from .models import Recipe, RecipeImage, RecipeIngredient, RecipeInstruction
from .services import import_from_url, normalize_import, sanitize_raster_upload


@login_required
def recipe_list(request):
    household_ids = request.user.memberships.filter(is_active=True).values_list("household_id", flat=True)
    recipes = Recipe.objects.filter(household_id__in=household_ids, archived_at__isnull=True)
    query = request.GET.get("q", "").strip()
    if query:
        recipes = recipes.filter(name__icontains=query)
    return render(request, "recipes/list.html", {"recipes": recipes.order_by("name")[:200], "query": query})


@login_required
def detail(request, recipe_id):
    recipe = get_object_or_404(Recipe.objects.select_related("household", "owner"), pk=recipe_id)
    if not request.user.memberships.filter(household=recipe.household, is_active=True).exists():
        raise PermissionDenied
    return render(request, "recipes/detail.html", {"recipe": recipe})


@login_required
@household_permission("recipe.create")
def create(request, household_id):
    form = RecipeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            recipe = form.save(commit=False)
            recipe.household = request.household
            recipe.owner = request.user
            recipe.save()
            for position, line in enumerate(form.cleaned_data["instructions_text"].splitlines(), 1):
                if line.strip():
                    RecipeInstruction.objects.create(recipe=recipe, position=position, text=line.strip())
            audit_event("recipe.created", actor=request.user, household=request.household, target=recipe, request=request)
        return redirect("recipes:detail", recipe_id=recipe.id)
    return render(request, "recipes/form.html", {"form": form, "household": request.household})


@login_required
def edit(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    membership = request.user.memberships.filter(household=recipe.household, is_active=True).first()
    if not membership or (recipe.owner != request.user and not membership.has_permission("recipe.edit")):
        raise PermissionDenied
    initial = {"instructions_text": "\n".join(recipe.instructions.values_list("text", flat=True))}
    form = RecipeForm(request.POST or None, instance=recipe, initial=initial)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            recipe = form.save()
            recipe.instructions.all().delete()
            for position, line in enumerate(form.cleaned_data["instructions_text"].splitlines(), 1):
                if line.strip():
                    RecipeInstruction.objects.create(recipe=recipe, position=position, text=line.strip())
        return redirect("recipes:detail", recipe_id=recipe.id)
    return render(request, "recipes/form.html", {"form": form, "household": recipe.household})


@login_required
def ingredient_create(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    membership = request.user.memberships.filter(household=recipe.household, is_active=True).first()
    if not membership or (recipe.owner != request.user and not membership.has_permission("recipe.edit")):
        raise PermissionDenied
    form = RecipeIngredientForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        line = form.save(commit=False)
        line.recipe = recipe
        if line.unit and line.ingredient.default_unit:
            if line.unit.dimension != line.ingredient.default_unit.dimension:
                form.add_error("unit", "Unit is incompatible with this ingredient.")
            else:
                line.save()
                return redirect("recipes:detail", recipe_id=recipe.id)
        else:
            line.save()
            return redirect("recipes:detail", recipe_id=recipe.id)
    return render(request, "recipes/ingredient_form.html", {"form": form, "recipe": recipe})


@login_required
@require_POST
def ingredient_delete(request, ingredient_id):
    line = get_object_or_404(RecipeIngredient.objects.select_related("recipe__household"), pk=ingredient_id)
    membership = request.user.memberships.filter(household=line.recipe.household, is_active=True).first()
    if not membership or (line.recipe.owner != request.user and not membership.has_permission("recipe.edit")):
        raise PermissionDenied
    recipe_id = line.recipe_id
    line.delete()
    return redirect("recipes:detail", recipe_id=recipe_id)


@login_required
@require_POST
def duplicate(request, recipe_id):
    source = get_object_or_404(Recipe, pk=recipe_id)
    membership = request.user.memberships.filter(household=source.household, is_active=True).first()
    if not membership or not membership.has_permission("recipe.create"):
        raise PermissionDenied
    ingredients = list(source.recipe_ingredients.all())
    instructions = list(source.instructions.all())
    with transaction.atomic():
        source.pk = None
        source.name = f"{source.name} (kopi)"
        source.owner = request.user
        source.save()
        for line in ingredients:
            line.pk = None
            line.recipe = source
            line.save()
        for step in instructions:
            step.pk = None
            step.recipe = source
            step.save()
    return redirect("recipes:edit", recipe_id=source.id)


@login_required
@household_permission("recipe.create")
def import_recipe(request, household_id):
    form = RecipeImportForm(request.POST or None)
    preview = None
    if request.method == "POST" and form.is_valid():
        try:
            raw = import_from_url(form.cleaned_data["payload"]) if form.cleaned_data["method"] == "url" else json.loads(form.cleaned_data["payload"])
            preview = normalize_import(raw)
        except (ValidationError, json.JSONDecodeError, ValueError) as error:
            form.add_error("payload", error)
        if preview and request.POST.get("confirm") == "yes":
            with transaction.atomic():
                recipe = Recipe.objects.create(
                    household=request.household,
                    owner=request.user,
                    name=preview["name"],
                    description=preview["description"],
                    servings=preview["servings"],
                    source_url=preview["source_url"],
                    attribution=preview["source_url"],
                )
                for index, text in enumerate(preview["instructions"], 1):
                    RecipeInstruction.objects.create(recipe=recipe, position=index, text=text)
            return redirect("recipes:edit", recipe_id=recipe.id)
    return render(request, "recipes/import.html", {"form": form, "preview": preview, "household": request.household})


@login_required
def export_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    if not request.user.memberships.filter(household=recipe.household, is_active=True).exists():
        raise PermissionDenied
    data = {
        "@context": "https://schema.org",
        "@type": "Recipe",
        "name": recipe.name,
        "description": recipe.description,
        "recipeYield": str(recipe.servings),
        "recipeInstructions": list(recipe.instructions.values_list("text", flat=True)),
        "recipeIngredient": [
            f"{item.quantity or ''} {item.unit or ''} {item.ingredient.name_da}".strip()
            for item in recipe.recipe_ingredients.select_related("ingredient", "unit")
        ],
    }
    response = JsonResponse(data, json_dumps_params={"indent": 2, "ensure_ascii": False})
    response["Content-Disposition"] = f'attachment; filename="recipe-{recipe.id}.json"'
    return response


@login_required
def upload_image(request, recipe_id):
    recipe = get_object_or_404(Recipe, pk=recipe_id)
    membership = request.user.memberships.filter(household=recipe.household, is_active=True).first()
    if not membership or (recipe.owner != request.user and not membership.has_permission("recipe.edit")):
        raise PermissionDenied
    form = RecipeImageForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        try:
            content = sanitize_raster_upload(form.cleaned_data["image"])
        except ValidationError as error:
            form.add_error("image", error)
        else:
            image = RecipeImage(recipe=recipe, alt_text=form.cleaned_data["alt_text"], uploaded_by=request.user)
            image.image.save(content.name, content, save=True)
            return redirect("recipes:detail", recipe_id=recipe.id)
    return render(request, "recipes/image_form.html", {"form": form, "recipe": recipe})


@login_required
def serve_image(request, image_id):
    image = get_object_or_404(RecipeImage.objects.select_related("recipe__household"), id=image_id)
    if not request.user.memberships.filter(household=image.recipe.household, is_active=True).exists():
        raise PermissionDenied
    response = FileResponse(image.image.open("rb"), content_type="image/jpeg")
    response["Content-Disposition"] = f'inline; filename="recipe-{image.id}.jpg"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, max-age=3600"
    return response
