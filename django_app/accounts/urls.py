from django.conf.urls import url
from django.contrib.auth.views import login

from .views import profile

app_name = 'accounts'

urlpatterns = [
    url(r'^login/$', login, name='login', kwargs={
        'template_name': 'accounts/login.html',
    }),
    url(r'profile/$', profile, name='profile'),
]