# این خط رو به pharmacy/urls.py اضافه کن — بعد از خط calculator:
path("drug-bank/", views.drug_bank, name="drug_bank"),

# و این دو تا view رو هم باید به views.py اضافه کنی:

# ══════════════════════════════════════════════════════════════════
#  بانک دارو
# ══════════════════════════════════════════════════════════════════

@login_required
def drug_bank(request):
    from .models import Drug, DrugCategory
    q = request.GET.get('q', '')
    category_id = request.GET.get('category', '')
    form_filter = request.GET.get('form', '')
    otc_filter = request.GET.get('otc', '')

    qs = Drug.objects.filter(is_active=True)
    if q:
        qs = qs.filter(
            Q(name_fa__icontains=q) | Q(name_en__icontains=q) |
            Q(brand_name__icontains=q) | Q(active_ingredient__icontains=q) |
            Q(indications__icontains=q) | Q(search_keywords__icontains=q)
        )
    if category_id:
        qs = qs.filter(category_id=category_id)
    if form_filter:
        qs = qs.filter(drug_form=form_filter)
    if otc_filter:
        qs = qs.filter(otc_rx=otc_filter)

    categories = DrugCategory.objects.all()
    total = qs.count()

    ctx = {
        **base_context(request),
        'drugs': qs[:200],
        'categories': categories,
        'search_query': q,
        'selected_category': category_id,
        'selected_form': form_filter,
        'selected_otc': otc_filter,
        'total': total,
        'form_choices': Drug.FORM_CHOICES,
        'otc_choices': Drug.OTCPX_CHOICES,
    }
    return render(request, 'pharmacy/drug_bank.html', ctx)


@login_required
@require_POST
def drug_to_product(request, pk):
    """اضافه کردن دارو از بانک دارو به محصولات"""
    from .models import Drug
    drug = get_object_or_404(Drug, pk=pk, is_active=True)
    code = f"DRG-{drug.pk:05d}"
    if not Product.objects.filter(code=code, is_deleted=False).exists():
        Product.objects.create(
            name=drug.name_fa,
            code=code,
            price=0,
            description=drug.indications or '',
            is_active=False,
        )
        return JsonResponse({'success': True, 'message': f'داروی «{drug.name_fa}» به محصولات اضافه شد.'})
    return JsonResponse({'success': False, 'message': 'این دارو قبلاً اضافه شده است.'})