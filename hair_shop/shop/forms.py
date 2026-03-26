from django import forms

from hair_shop.shop.models import Product


class SmartSearchForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].required = False
        self.fields["final_price"].required = False
        self.fields["hair_shade"].required = False
        self.fields["category"].empty_label = "все категории"
        self.fields["hair_shade"].empty_label = "все оттенки"
        

    class Meta:
        model = Product
        fields = ('category', 'final_price', 'hair_shade'  )
        widgets = {
            'category': forms.Select(attrs={'class': 'form-control'}),
            'final_price': forms.NumberInput(
                attrs={
                    "type": "range",
                    "step": "100",
                    "min": "0",
                }
            ),
            'hair_shade': forms.Select(attrs={'class': 'form-control'}),
        }