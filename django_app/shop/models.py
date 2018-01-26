from uuid import uuid4

from django.conf import settings
from django.db import models

from iamport import Iamport


class Item(models.Model):
    name = models.CharField(
        max_length=100,
    )
    desc = models.TextField(blank=True)
    amount = models.PositiveIntegerField()
    photo = models.ImageField()
    is_public = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def api(self):
        # FIXME : 결제 결과에 대한 컨트롤을 할 경우 아임포트 API를 통한 확인 후에 변경을 해야 함.
        # 브라우저에서 결제 후 실제 아임포트 결제 요청 리스트와 비교하여 결제가 확실히 완료 됐는지 확인 후 DB에 업데이트 한다.
        # 확인 작업을 거치지 않을 경우 개발자 도구 혹은 그 외의 부정한 방법으로 결제 스크립트를 변죠 할 경우 결제가 완료 되지 않아도 DB로 결제 완료 된 것으로 갱신 될 수 있기 때문 !!
        return Iamport(settings.IAMPORT_API_KEY, settings.IAMPORT_API_SECRET)

    def update(self, commit=True, meta=None):
        if self.imp_uid:
            self.meta = meta or self.api.find(imp_uid=self.imp_uid) # merchant_uid는 반드시 매칭 돼어야 함
            # assert = 우측의 조건에 해당 하는 결과가 False일 경우 오류 발생
            assert str(self.merchant_uid) == self.meta['merchant_uid']
            self.status = self.meta['status']
        if commit:
            self.save()


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    item = models.ForeignKey(Item)
    merchant_uid = models.UUIDField(default=uuid4  , editable=False)
    imp_uid = models.CharField(max_length=100, blank=True)
    name = models.CharField(max_length=100, verbose_name='상품명')
    amount = models.PositiveIntegerField(verbose_name='결제금액')
    status = models.CharField(
        max_length=9,
        choices=(
            ('ready', '미결제'),
            ('paid', '결제완료'),
            ('cancelled', '결제취소'),
            ('failed', '결제실패'),
        ),
        default='ready',
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('-id',)