from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class SiteAssets(models.Model):
    site_assets_name = models.CharField(max_length=200, verbose_name='Название')
    image = models.ImageField(upload_to='site_assets/', blank=True, null=True, verbose_name='Изображение')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    description = models.TextField(blank=True, verbose_name='Описание')
    note = models.TextField(blank=True, verbose_name='Примечание')

    class Meta:
        verbose_name = 'логотипы, слоганы и прочее'
        verbose_name_plural = 'логотипы, слоганы и прочее'

    def __str__(self):
        return self.site_assets_name


class Category(models.Model):
    """Основная категория товаров"""
    name = models.CharField(max_length=200, verbose_name='Название категории')
    slug = models.SlugField(max_length=200, unique=True, verbose_name='URL')
    description = models.TextField(blank=True, verbose_name='Описание')
    image = models.ImageField(upload_to='categories/', blank=True, null=True, verbose_name='Изображение')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['-created_at', 'name']
        indexes = [
            models.Index(fields=['slug']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return f'/catalog/{self.slug}/'


class Product(models.Model):
    HAIRSHADES = (
        ('light', 'Светлый'),
        ('dark', 'Темный'),
        ('medium', 'Средний'),
        ('red', 'Рыжий'),
        ('combined', 'Смешанный'),
        ('other', 'Другой'),
    )

    """Товар"""
    name = models.CharField(max_length=200, verbose_name='Название', blank=False, null=False, default='')
    slug = models.SlugField(max_length=255, unique=False, verbose_name='URL')
    category = models.ManyToManyField(Category, related_name='products', verbose_name='Категории')
    article = models.CharField(max_length=200, verbose_name='Артикул')
    main_image = models.ImageField(upload_to='products/', blank=True, null=True, verbose_name='Главное изображение')
    start_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Начальная цена')
    discount_percentage = models.IntegerField('Скидка %', default=0,
                                              validators=[MinValueValidator(0), MaxValueValidator(100)])
    hair_shade = models.CharField(max_length=200, choices=HAIRSHADES, verbose_name='Оттенок', blank=True, default='other')
    color = models.CharField(max_length=200, verbose_name='Цвет', blank=True, default='')
    hair_length = models.CharField(max_length=200, verbose_name='Длина волос', blank=True, default='')
    hair_width = models.CharField(max_length=200, verbose_name='Ширина волос', blank=True, default='')
    hair_material = models.CharField(max_length=200, verbose_name='Материал волос', blank=True, default='')
    number_of_strands = models.CharField(max_length=200, verbose_name='Количество прядей', blank=True, default='')
    hair_extension_method = models.CharField(max_length=200, verbose_name='Метод прикрепления', blank=True, default='')
    hair_type = models.CharField(max_length=200, verbose_name='Тип волос или канекалона', blank=True, default='')
    country_of_origin = models.CharField(max_length=200, verbose_name='Страна происхождения', blank=True, default='')
    description = models.TextField(blank=True, verbose_name='Описание',  default='')
    kit = models.CharField(max_length=200, verbose_name='Комплектация', blank=True, default='')
    decoration = models.CharField(max_length=200, verbose_name='Декоративные элементы', blank=True, default='')
    package = models.CharField(max_length=200, verbose_name='размер упаковки', blank=True, default='')
    rating = models.DecimalField(max_digits=2, decimal_places=1, verbose_name='Рейтинг', blank=True, default=4.5)
    is_hit = models.BooleanField(default=False, verbose_name='Хит продаж')
    is_available = models.BooleanField(default=True, verbose_name='Доступность')
    parent = models.ForeignKey(
        'self',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='variants',
        verbose_name='Серия (родительский товар)'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at', 'article']
        indexes = [
            models.Index(fields=['is_available']),
        ]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        slug = self.slug or (self.parent.slug if self.parent else '')
        return f'/product_page/{slug}/{self.id}/'    

    @property
    def final_price(self):
        return self.start_price - (self.start_price * self.discount_percentage / 100)

    def get_field(self, field_name):
        """Получить поле с фолбеком на родителя"""
        val = getattr(self, field_name, None)
        if not val and self.parent:
            return getattr(self.parent, field_name, None)
        return val


class ProductImage(models.Model):
    """Дополнительные изображения товара"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='images', verbose_name='Товар')
    image = models.ImageField('Изображение', upload_to='products/gallery/')
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    class Meta:
        verbose_name = 'Изображение товара'
        verbose_name_plural = 'Изображения товара'

    def __str__(self):
        return f"Изображение для {self.product.name}"


class Review(models.Model):
    """Отзывы о товарах"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='reviews', verbose_name='Товар')
    user = models.ForeignKey("users.User", on_delete=models.CASCADE,
                             related_name='reviews', verbose_name='Пользователь')
    rating = models.PositiveIntegerField('Оценка',
                                         validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField('Заголовок', max_length=200)
    text = models.TextField('Текст отзыва')

    # Модерация
    is_approved = models.BooleanField('Одобрен', default=False)

    # Метаданные
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']
        unique_together = ['product', 'user']  # Один отзыв от пользователя на товар

    def __str__(self):
        return f"Отзыв от {self.user.username} на {self.product.name}"


class Favorite(models.Model):
    """Избранные товары"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE,
                             related_name='favorites', verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='favorited_by', verbose_name='Товар')
    created_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    class Meta:
        verbose_name = 'Избранное'
        verbose_name_plural = 'Избранное'
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username} - {self.product.name}"


class Cart(models.Model):
    """Корзина пользователя"""
    user = models.OneToOneField('users.User', on_delete=models.CASCADE,
                                related_name='cart', verbose_name='Пользователь')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    class Meta:
        verbose_name = 'Корзина'
        verbose_name_plural = 'Корзины'

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


class CartItem(models.Model):
    """Товар в корзине"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE,
                             related_name='items', verbose_name='Корзина')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='cart_items', verbose_name='Товар')
    quantity = models.PositiveIntegerField('Количество', default=1,
                                           validators=[MinValueValidator(1)])
    added_at = models.DateTimeField('Дата добавления', auto_now_add=True)

    class Meta:
        verbose_name = 'Товар в корзине'
        verbose_name_plural = 'Товары в корзине'
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def total_price(self):
        """Стоимость позиции"""
        return self.product.final_price * self.quantity


class ViiwsHistory(models.Model):
    """История просмотров товаров пользователем"""
    user = models.ForeignKey('users.User', on_delete=models.CASCADE,
                             related_name='view_history', verbose_name='Пользователь')
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='viewed_by', verbose_name='Товар')

    class Meta:
        verbose_name = 'История просмотров'
        verbose_name_plural = 'Истории просмотров'
        unique_together = ['user', 'product']

    def __str__(self):
        return f"{self.user.username} просмотрел {self.product.name}"


