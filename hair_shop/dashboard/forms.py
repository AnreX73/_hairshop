from django import forms

from shop.models import Order, Product, Info, DeliveryZone


class OrderStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["status"]


class OrderShipForm(forms.ModelForm):
    """Отдельная форма для отправки — там ещё трек-номер"""

    class Meta:
        model = Order
        fields = ["tracking_number"]


class OrderPaymentStatusForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ["payment_status"]


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "article",
            "category",
            "price",
            "discount_percentage",
            "stock",
            "out_of_stock_behavior",
            "description",
            "color",
            "hair_length",
            "hair_width",
            "hair_material",
            "number_of_strands",
            "hair_extension_method",
            "hair_type",
            "country_of_origin",
            "kit",
            "decoration",
            "package",
            "packaging_weight",
            "packaging_length",
            "packaging_width",
            "packaging_height",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "out_of_stock_behavior": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Все поля — не обязательные по умолчанию (кроме name, article, category)
        required_fields = {"name", "article", "category", "price"}
        for name, field in self.fields.items():
            if name not in required_fields:
                field.required = False
            # Красивые плейсхолдеры
            field.widget.attrs.setdefault("class", "form-control")


class ProductHairLengthForm(forms.Form):
    product_id = forms.IntegerField(widget=forms.HiddenInput())
    hair_length = forms.IntegerField(
        required=True,
        min_value=0,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Введите длину волос"}
        ),
    )


class StartBannerForm(forms.ModelForm):
    """
    Форма редактирования стартового баннера.
    Поля name и slug заполняются автоматически — админ их не видит.
    """

    class Meta:
        model = Info
        fields = ['title', 'image', 'content', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Заголовок баннера (H1)',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control-file',
            }),
            'content': forms.Textarea(attrs={
                'class': 'form-control html-editor',
                'rows': 12,
                'placeholder': 'HTML-контент баннера...',
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
            }),
        }
        labels = {
            'title': 'Заголовок (H1)',
            'image': 'Изображение',
            'content': 'Контент (поддерживается HTML)',
            'is_active': 'Показывать баннер на сайте',
        }
        help_texts = {
            'content': 'Выводится на странице через фильтр <code>|safe</code> — можно использовать HTML-разметку.',
            'image': 'Если изображение не загружено, на странице будет показан логотип сайта.',
        }

    def clean_title(self):
        title = self.cleaned_data.get('title', '').strip()
        if not title:
            raise forms.ValidationError('Заголовок обязателен.')
        return title

    def save(self, commit=True):
        instance = super().save(commit=False)

        # Фиксируем имя — именно по нему ищется баннер на фронте
        instance.name = "Стартовый баннер"

        # Автогенерация slug из title (если ещё не задан)
        if not instance.slug:
            base_slug = self._transliterate(instance.title)
            slug = base_slug
            counter = 1
            # Проверка уникальности
            qs = Info.objects.filter(slug=slug)
            if instance.pk:
                qs = qs.exclude(pk=instance.pk)
            while qs.exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug

        if commit:
            instance.save()
        return instance

    @staticmethod
    def _transliterate(text: str) -> str:
        """Простая транслитерация кириллицы в латиницу для slug."""
        mapping = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'e',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            ' ': '-', '_': '-',
        }
        text = text.lower().strip()
        result = ''.join(mapping.get(ch, ch) for ch in text)
        # Оставляем только разрешённые символы
        result = slugify(result, allow_unicode=False)
        return result or 'banner'


class DeliveryZonePriceForm(forms.ModelForm):
    class Meta:
        model = DeliveryZone
        fields = ['price']
        widgets = {
            'price': forms.NumberInput(attrs={
                'class': 'price-input',
                'min': 0,
            })
        }