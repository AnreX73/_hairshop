from django import forms
from shop.models import Product, ProductImage



 
# Добавление вариантов к продукту
# Поля которые вариант никогда не меняет
# LOCKED_FIELDS = [
#     'name', 'category', 'hair_material', 'hair_extension_method',
#     'hair_type', 'country_of_origin', 'kit', 'decoration', 'package',
# ]

# # Поля которые можно подправить для варианта
# EDITABLE_INHERITED_FIELDS = [
#     'description', 'hair_length', 'hair_width', 'number_of_strands',
#     'start_price', 'discount_percentage', 'rating', 'is_hit',
# ]

# class ProductForm(forms.ModelForm):
#     class Meta:
#         model = Product
#         exclude = ['created_at', 'updated_at', 'slug']
#         widgets = {
#             'description': forms.Textarea(attrs={'rows': 4}),
#             'category': forms.CheckboxSelectMultiple(),
#         }

#     def __init__(self, *args, parent=None, **kwargs):
#         super().__init__(*args, **kwargs)
#         self.parent = parent

#     if parent:
#         self.fields['parent'].initial = parent
#         self.fields['parent'].widget = forms.HiddenInput()

#         for field in EDITABLE_INHERITED_FIELDS + LOCKED_FIELDS:
#             if field not in self.fields:
#                 continue

#             # M2M поля обрабатываем отдельно
#             model_field = Product._meta.get_field(field)
#             if model_field.many_to_many:
#                 self.initial[field] = getattr(parent, field).all()
#             else:
#                 self.initial[field] = getattr(parent, field)

#         for field in LOCKED_FIELDS:
#             if field in self.fields:
#                 self.fields[field].widget.attrs['readonly'] = True
#                 self.fields[field].widget.attrs['style'] = 'background: #f5f5f5; color: #888;'

#     def clean(self):
#         cleaned_data = super().clean()
#         if self.parent:
#             for field in LOCKED_FIELDS:
#                 model_field = Product._meta.get_field(field)
#                 if model_field.many_to_many:
#                     cleaned_data[field] = getattr(self.parent, field).all()
#                 else:
#                     cleaned_data[field] = getattr(self.parent, field)
#         return cleaned_data