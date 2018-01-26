import json

from django import forms
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
            'iamport_shop_id': 'iamport', # FIXME: 각자의 iamport 결제 상점 아이디로 변경 ( 'iamport'는 테스트용 아이디 )
        })

    def save(self):
        order = super().save(commit=False)
        order.status = 'paid'
        # FIXME : 아임포트 API를 통한 확인 후에 변경을 해야 함.
        # 브라우저에서 결제 후 실제 아임포트 결제 요청 리스트와 비교하여 결제가 확실히 완료 됐는지 확인 후 DB에 업데이트 한다.
        # 확인 작업을 거치지 않을 경우 개발자 도구 혹은 그 외의 부정한 방법으로 결제 스크립트를 변죠 할 경우 결제가 완료 되지 않아도 DB로 결제 완료 된 것으로 갱신 될 수 있기 때문!!
        order.save()
        return order
