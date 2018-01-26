import json

from django import forms
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.encoding import smart_text
from django.utils.safestring import mark_safe

from shop.models import Order


class PayForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ('imp_uid', )

    def as_iamport(self):
        hidden_fields = mark_safe(''.join(smart_text(field) for field in self.hidden_fields()))

        fields = {
            'merchant_uid': str(self.instance.merchant_uid),
            'name': self.instance.name,
            'amount': self.instance.amount,
        }

        return hidden_fields + render_to_string('shop/_iamport.html', {
            'json_fields': mark_safe(json.dumps(fields, ensure_ascii=False)),
            'iamport_shop_id': settings.IAMPORT_SHOP_ID, # FIXME: 각자의 iamport 결제 상점 아이디로 변경 ( 'iamport'는 테스트용 아이디 )
        })

    def save(self):
        order = super().save(commit=False)
        order.update()
        return order
