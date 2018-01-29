from datetime import datetime
from uuid import uuid4

import pytz
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import intcomma
from django.db import models
from django.http import Http404
from django.utils.safestring import mark_safe

from iamport import Iamport
from jsonfield import JSONField


def named_property(name):
    def wrap(fn):
        fn.short_description = name
        return property(fn)
    return wrap


def timestamp_to_datetime(timestamp):
    if timestamp:
        tz = pytz.timezone(settings.TIME_ZONE)
        return datetime.utcfromtimestamp(timestamp).replace(tzinfo=tz)
    return None


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
    meta = JSONField(blank=True, default={})
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    is_ready = property(lambda self: self.status == 'ready')
    is_paid = property(lambda self: self.status == 'paid')
    is_paid_ok = property(lambda self: self.status == 'paid' and self.amount == self.meta.get('amount'))
    is_cancelled = property(lambda self: self.status == 'cancelled')
    is_failed = property(lambda self: self.status == 'failed')
    receipt_url = named_property('영수증')(lambda self: self.meta.get('receipt_url'))
    cancel_reason = named_property('취소이유')(lambda self: self.meta.get('cancel_reason'))
    fail_reason = named_property('실패이유')(lambda self: self.meta.get('fail_reason', ''))
    paid_at = named_property('결제일시')(lambda self: timestamp_to_datetime(self.meta.get('paid_at')))
    failed_at = named_property('실패일시')(lambda self: timestamp_to_datetime(self.meta.get('failed_at')))
    cancelled_at = named_property('취소일시')(lambda self: timestamp_to_datetime(self.meta.get('cancelled_at')))

    class Meta:
        ordering = ('-id',)


    @property
    def api(self):
        # FIXME : 결제 결과에 대한 컨트롤을 할 경우 아임포트 API를 통한 확인 후에 변경을 해야 함.
        # 브라우저에서 결제 후 실제 아임포트 결제 요청 리스트와 비교하여 결제가 확실히 완료 됐는지 확인 후 DB에 업데이트 한다.
        # 확인 작업을 거치지 않을 경우 개발자 도구 혹은 그 외의 부정한 방법으로 결제 스크립트를 변죠 할 경우 결제가 완료 되지 않아도 DB로 결제 완료 된 것으로 갱신 될 수 있기 때문 !!
        return Iamport(settings.IAMPORT_API_KEY, settings.IAMPORT_API_SECRET)

    def update(self, commit=True, meta=None):
        if self.imp_uid:
            try:
                self.meta = meta or self.api.find(imp_uid=self.imp_uid) # merchant_uid는 반드시 매칭 돼어야 함
            except Iamport.HttpError:
                raise Http404('Not found {}'.format(self.imp_uid))
            # assert = 우측의 조건에 해당 하는 결과가 False일 경우 오류 발생
            assert str(self.merchant_uid) == self.meta['merchant_uid']
            self.status = self.meta['status']
        if commit:
            self.save()

    def cancel(self, reason=None, commit=True):
        try:
            meta = self.api.cancel(reason=reason, imp_uid=self.imp_uid)
            assert str(self.merchant_uid) == self.meta['merchant_uid']
            self.update(commit=commit, meta=meta)
        except Iamport.ResponseError as e:
            self.update(commit=commit)
        if commit:
            self.save()

    @named_property('결제금액')
    def amount_html(self):
        return mark_safe('<div style="float: right;">{0}</div>'.format(intcomma(self.amount)))

    @named_property('처리결과')
    def status_html(self):
        cls, text_color = '', ''

        help_text = ''
        if self.is_ready:
            cls, text_color = 'fa fa-shopping-cart', '#ccc'
        elif self.is_paid_ok:
            cls, text_color = 'fa fa-check-circle', 'green'
        elif self.is_cancelled:
            cls, text_color = 'fa fa-times', 'gray'
            help_text = self.cancel_reason
        elif self.is_failed:
            cls, text_color = 'fa fa-ban', 'red'
            help_text = self.fail_reason
        html = '''
            <span style="color: {text_color};" title="this is title">
            <i class="{class_names}"></i>
            {label}
            </span>'''.format(class_names=cls, text_color=text_color, label=self.get_status_display())
        if help_text:
            html += '<br/>' + help_text
        return mark_safe(html)

    @named_property('영수증 링크')
    def receipt_link(self):
        if self.is_paid_ok and self.receipt_url:
            return mark_safe('<a href="{0}" target="_blank">영수증</a>'.format(self.receipt_url))