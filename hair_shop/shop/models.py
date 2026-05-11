from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from .utils import make_slug

from .validators import validate_review_media


class SiteAssets(models.Model):
    site_assets_name = models.CharField(max_length=200, verbose_name="Название")
    image = models.ImageField(
        upload_to="site_assets/", blank=True, null=True, verbose_name="Изображение"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    description = models.TextField(blank=True, verbose_name="Описание")
    note = models.TextField(blank=True, verbose_name="Примечание")

    class Meta:
        verbose_name = "логотипы, слоганы и прочее"
        verbose_name_plural = "логотипы, слоганы и прочее"

    def __str__(self):
        return self.site_assets_name


class Category(models.Model):
    """Основная категория товаров"""

    name = models.CharField(max_length=200, verbose_name="Название категории")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL")
    description = models.TextField(blank=True, verbose_name="Описание")
    image = models.ImageField(
        upload_to="categories/", blank=True, null=True, verbose_name="Изображение"
    )
    is_active = models.BooleanField(default=True, verbose_name="Активна")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        ordering = ["-created_at", "name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f"/catalog/{self.slug}/"


class Product(models.Model):
    OUT_OF_STOCK_BEHAVIOR = [
        ("hide", "Скрыть товар"),
        ("show", "Показывать с пометкой"),
    ]

    name = models.CharField(max_length=200, verbose_name="Наименование", default="")
    article = models.CharField(max_length=200, verbose_name="Артикул", default="")
    product_group = models.CharField(max_length=200, verbose_name="Группа", default="")

    group_slug = models.SlugField(
        max_length=255,
        verbose_name="URL группы",
        default="",
        blank=True,
        db_index=True,  # ускоряет фильтрацию, но не запрещает дубли
    )

    note_for_manager = models.TextField(
        blank=True, default="", verbose_name="Примечание для менеджера"
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="products",
        verbose_name="Категория",
        default=1,
    )
    description = models.TextField(blank=True, default="", verbose_name="Описание")
    color = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Цвет"
    )
    hair_length = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Длина волос"
    )
    hair_width = models.CharField(
        max_length=200, blank=True, null=True, verbose_name="Ширина волос"
    )
    hair_material = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Состав"
    )
    number_of_strands = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Количество прядей"
    )
    hair_extension_method = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Способ наращивания волос"
    )
    hair_type = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Вид волос"
    )
    country_of_origin = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Страна производства"
    )
    kit = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Комплектация"
    )
    decoration = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Декоративные элементы"
    )
    package = models.CharField(
        max_length=200, blank=True, default="", verbose_name="Упаковка"
    )
    packaging_weight = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Вес упаковки (кг)",
    )
    packaging_length = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        verbose_name="Длина упаковки (см)",
    )
    packaging_width = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        verbose_name="Ширина упаковки (см)",
    )
    packaging_height = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        blank=True,
        null=True,
        verbose_name="Высота упаковки (см)",
    )
    price = models.PositiveIntegerField(default=0, verbose_name="Цена")
    discount_percentage = models.IntegerField(
        default=0,
        verbose_name="Скидка",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    # models.py
    stock = models.PositiveIntegerField(default=10, verbose_name="Количество на складе")
    out_of_stock_behavior = models.CharField(
        "При отсутствии товара",
        max_length=10,
        choices=OUT_OF_STOCK_BEHAVIOR,
        default="hide",
    )

    rating = models.DecimalField(
        max_digits=3, decimal_places=1, default=0, verbose_name="Рейтинг"
    )
    reviews_count = models.PositiveIntegerField(
        default=0, verbose_name="Количество отзывов"
    )
    popularity = models.IntegerField(
        default=0, verbose_name="Популярность", db_index=True
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ["-created_at", "article"]
        indexes = [
            models.Index(fields=["group_slug"]),
        ]

    def save(self, *args, **kwargs):
        # Генерируем slug ТОЛЬКО при создании (если поле пустое)
        if not self.group_slug:
            raw_value = f"{self.name}_{self.product_group}"
            self.group_slug = make_slug(raw_value)

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.product_group} — {self.name or self.article}"

    def get_absolute_url(self):
        return f"/product_page/{self.group_slug}/{self.id}/"

    @property
    def final_price(self):
        return int(self.price * (1 - self.discount_percentage / 100))

    @property
    def is_available(self):
        return self.stock > 0

    @property
    def is_hit(self):
        from django.core.cache import cache

        hit_ids = cache.get("hit_product_ids")
        if hit_ids is None:
            hit_ids = set(
                Product.objects.order_by("-popularity").values_list("id", flat=True)[
                    :24
                ]
            )
            cache.set("hit_product_ids", hit_ids, timeout=3600)
        return self.pk in hit_ids

    @property
    def is_visible(self):
        if self.stock > 0:
            return True
        return self.out_of_stock_behavior == "show"

    @property
    def main_image(self):
        # Если есть prefetch — берём из кэша, без запроса
        if hasattr(self, "prefetched_images"):
            first = self.prefetched_images[0] if self.prefetched_images else None
        else:
            # Fallback для мест где prefetch не делался (например detail view)
            first = self.images.filter(media_type="image").first()

        return first.image if first else None


# models.py
class ProductImage(models.Model):
    TYPE_CHOICES = (
        ("image", "Изображение"),
        ("video", "Видео файл"),
    )
    STATUS_CHOICES = (
        ("pending", "Ожидает обработки"),
        ("processing", "Обрабатывается"),
        ("done", "Готово"),
        ("error", "Ошибка"),
    )

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="images", verbose_name="Товар"
    )
    media_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default="image")
    image = models.ImageField(
        "Фото", upload_to="products/gallery/", blank=True, null=True
    )
    image_compressed = models.ImageField(
        "Сжатое фото", upload_to="products/gallery/compressed/", blank=True, null=True
    )
    video = models.FileField(
        upload_to="products/videos/", blank=True, null=True, verbose_name="Видео"
    )
    video_compressed = models.FileField(
        upload_to="products/videos/compressed/",
        blank=True,
        null=True,
        verbose_name="Сжатое видео",
    )
    order = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        ordering = ["order"]
        verbose_name = "Медиа файл"
        verbose_name_plural = "Галерея товара"

    def __str__(self):
        return f"{self.product} - {self.media_type}"

    @property
    def preview_url(self):
        if self.media_type == "image":
            f = self.image_compressed or self.image
            return f.url if f else None
        else:
            f = self.video_compressed or self.video
            return f.url if f else None

    @property
    def display_image(self):
        """Возвращает сжатое фото если есть, иначе оригинал"""
        if self.image_compressed:
            return self.image_compressed
        return self.image


class Favorite(models.Model):
    """Избранные товары"""

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="Пользователь",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="favorited_by",
        verbose_name="Товар",
    )
    created_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Избранное"
        verbose_name_plural = "Избранное"
        unique_together = ["user", "product"]

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Cart(models.Model):
    """Корзина пользователя"""

    user = models.OneToOneField(
        "users.User",
        on_delete=models.CASCADE,
        related_name="cart",
        verbose_name="Пользователь",
    )
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина {self.user.username}"

    @property
    def total_price(self):
        """Общая стоимость товаров в корзине"""
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        """Общее количество товаров"""
        return sum(item.quantity for item in self.items.all())

    total_items.fget.short_description = "Количество товаров"
    total_price.fget.short_description = "Общая стоимость"


class CartItem(models.Model):
    """Товар в корзине"""

    cart = models.ForeignKey(
        Cart, on_delete=models.CASCADE, related_name="items", verbose_name="Корзина"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.CASCADE,
        related_name="cart_items",
        verbose_name="Товар",
    )
    quantity = models.PositiveIntegerField(
        "Количество", default=1, validators=[MinValueValidator(1)]
    )
    added_at = models.DateTimeField("Дата добавления", auto_now_add=True)

    class Meta:
        verbose_name = "Товар в корзине"
        verbose_name_plural = "Товары в корзине"
        unique_together = ["cart", "product"]

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        """Стоимость позиции"""
        return self.product.final_price * self.quantity


class Order(models.Model):
    """Заказы"""

    STATUS_CHOICES = [
        ("pending", "Новый заказ!"),
        ("confirmed", "Подтвержден"),
        ("processing", "Собран"),
        ("shipped", "Отправлен"),
        ("delivered", "Доставлен"),
        ("cancelled", "Отменен"),
    ]

    PAYMENT_STATUS_CHOICES = [
        ("pending", "Ожидает оплаты"),
        ("paid", "Оплачен"),
        ("failed", "Ошибка оплаты"),
        ("refunded", "Возвращен"),
    ]

    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="orders",
        verbose_name="Пользователь",
    )

    assigned_manager = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="managed_orders",
        verbose_name="Менеджер",
    )
    tracking_number = models.CharField("Трек-номер", max_length=100, blank=True)
    # Статусы
    status = models.CharField(
        "Статус", max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    payment_status = models.CharField(
        "Статус оплаты",
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default="pending",
    )

    # Стоимость
    subtotal = models.IntegerField("Сумма товаров")
    delivery_cost = models.IntegerField("Стоимость доставки", default=0)
    total = models.IntegerField("Итого")

    # Контактная информация
    customer_name = models.CharField("ФИО", max_length=200)
    customer_email = models.EmailField("Email")
    customer_phone = models.CharField("Телефон", max_length=20)

    # Адрес доставки
    delivery_address = models.TextField("Адрес доставки")
    delivery_city = models.CharField("Город", max_length=100)
    delivery_postal_code = models.CharField("Индекс", max_length=20)

    # Дополнительно
    notes = models.TextField("Комментарий к заказу", blank=True)

    # Метаданные
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Заказ #{self.order_number}"

    def get_total_items(self):
        """Общее количество товаров в заказе"""
        return self.items.aggregate(total=models.Sum("quantity"))["total"] or 0

    @property
    def order_number(self):
        """Генерация номера заказа user_id - order_id"""
        return f"{self.user_id}-{self.id}"

    @property
    def items_editable(self):
        return self.status in ("pending", "confirmed")

    @property
    def all_items_collected(self):
        return not self.items.filter(is_collected=False).exists()


class OrderItem(models.Model):
    """Товар в заказе"""

    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items", verbose_name="Заказ"
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.PROTECT,
        related_name="order_items",
        verbose_name="Товар",
    )
    product_name = models.CharField("Название товара", max_length=300)
    product_price = models.PositiveIntegerField("Цена товара")
    quantity = models.PositiveIntegerField(
        "Количество", validators=[MinValueValidator(1)]
    )
    is_collected = models.BooleanField("Товар собран", default=False)

    class Meta:
        verbose_name = "Товар в заказе"
        verbose_name_plural = "Товары в заказе"

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"

    @property
    def total_price(self):
        """Стоимость позиции"""
        return self.product_price * self.quantity


class Review(models.Model):
    """Отзывы о товарах"""

    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="reviews", verbose_name="Товар"
    )
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="reviews",
        verbose_name="Пользователь",
    )
    rating = models.PositiveIntegerField(
        "Оценка", validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    title = models.CharField("Заголовок", max_length=200)
    text = models.TextField("Текст отзыва")

    # Модерация
    is_approved = models.BooleanField("Одобрен", default=False)
    review_answer = models.TextField("Ответ на отзыв", blank=True, null=True)

    # Метаданные
    created_at = models.DateTimeField("Дата создания", auto_now_add=True)
    updated_at = models.DateTimeField("Дата обновления", auto_now=True)

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        ordering = ["-created_at"]
        unique_together = ["product", "user"]  # Один отзыв от пользователя на товар

    def __str__(self):
        return f"Отзыв от {self.user.username} на {self.product}"

    MAX_PHOTOS = 5
    MAX_VIDEOS = 1

    def clean(self):
        """Пользователь может оставить отзыв только на доставленный и оплаченный товар"""
        from django.core.exceptions import ValidationError

        has_valid_order = Order.objects.filter(
            user=self.user,
            status="delivered",
            payment_status="paid",
            items__product=self.product,
        ).exists()

        if not has_valid_order:
            raise ValidationError(
                "Вы можете оставить отзыв только о товаре из доставленного и оплаченного заказа."
            )

    def save(self, *args, **kwargs):
        self.full_clean()  # вызываем clean() при сохранении
        super().save(*args, **kwargs)


class ReviewMedia(models.Model):
    MEDIA_TYPE_CHOICES = [
        ("photo", "Фото"),
        ("video", "Видео"),
    ]
    STATUS_CHOICES = [
        ("pending", "Ожидает"),
        ("processing", "Обрабатывается"),
        ("done", "Готово"),
        ("error", "Ошибка"),
    ]

    review = models.ForeignKey(
        Review, on_delete=models.CASCADE, related_name="media", verbose_name="Отзыв"
    )
    media_type = models.CharField("Тип", max_length=10, choices=MEDIA_TYPE_CHOICES)
    file = models.FileField(
        "Файл",
        upload_to="reviews/%Y/%m/",
        blank=True,
        validators=[validate_review_media],
    )
    file_compressed = models.FileField(
        "Сжатый файл", upload_to="reviews/compressed/%Y/%m/", blank=True, null=True
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Медиафайл отзыва"
        verbose_name_plural = "Медиафайлы отзывов"
        ordering = ["order"]

    def __str__(self):
        return f"{self.review} - {self.media_type}"

    @property
    def preview_url(self):
        f = self.file_compressed or self.file
        return f.url if f else None

    def clean(self):
        from django.core.exceptions import ValidationError
        import os

        ext = os.path.splitext(self.file.name)[1].lower()
        is_video = ext in {".mp4", ".mov", ".avi"}
        self.media_type = "video" if is_video else "photo"

        existing = self.review.media.filter(media_type=self.media_type)
        if self.pk:
            existing = existing.exclude(pk=self.pk)
        limit = Review.MAX_VIDEOS if is_video else Review.MAX_PHOTOS
        if existing.count() >= limit:
            raise ValidationError(
                f'Максимум {limit} файлов типа "{self.media_type}" на отзыв.'
            )


class Contact(models.Model):
    # Предустановленные типы для удобства и иконок
    TYPE_CHOICES = [
        ("phone", "Телефон"),
        ("email", "Email"),
        ("address", "Адрес"),
        ("social", "Соцсеть / Мессенджер"),
    ]

    contact_type = models.CharField(
        "Тип контакта", max_length=20, choices=TYPE_CHOICES, default="phone"
    )
    label = models.CharField(
        "Заголовок", max_length=50, help_text="Напр: 'Отдел продаж' или 'WhatsApp'"
    )
    slug = models.SlugField(
        "Слаг",
        max_length=50,
        help_text="Цифры, латиница, дефисы. БЕЗ пробелов!",
        unique=True,
    )
    value = models.CharField(
        "Значение", max_length=200, help_text="Сам номер, почта или адрес"
    )
    url = models.URLField(
        "Ссылка",
        blank=True,
        help_text="Для соцсетей или кликабельного номера (tel:+7...)",
    )

    contact_icon = models.ImageField("Иконка", upload_to="contacts/", blank=True)
    svg_icon = models.TextField(
        "SVG иконка, если есть или код карты если это карта)",
        blank=True,
        help_text="Вставьте XML-код иконки <svg>...</svg> без параметров width/height",
    )
    sort_order = models.PositiveIntegerField("Порядок сорт.", default=0)
    is_active = models.BooleanField("Отображать на сайте", default=True)

    class Meta:
        verbose_name = "Контакт"
        verbose_name_plural = "Контакты магазина"
        ordering = ["sort_order"]  # Чтобы контакты всегда шли в нужном вам порядке

    def __str__(self):
        return f"{self.label}: {self.value}"


class Info(models.Model):
    name = models.CharField("Название", max_length=100, default="Информация")
    title = models.CharField("Заголовок", max_length=100)
    slug = models.SlugField(
        "Слаг",
        max_length=50,
        help_text="Цифры, латиница, дефисы. БЕЗ пробелов!",
        unique=True,
    )
    content = models.TextField("Содержимое")
    image = models.ImageField("Изображение", upload_to="info/", blank=True)
    is_active = models.BooleanField("Отображать на сайте", default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Информация"
        verbose_name_plural = "Информация"
