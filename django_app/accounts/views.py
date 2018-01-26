from django.contrib.auth.decorators import login_required
from django.shortcuts import render

# Create your views here.
from shop.models import Order


@login_required
def profile(request):
    order_list = Order.objects.filter(user=request.user)
    # order_list = request.user.order_set.all()

    context = {
        'order_list': order_list,
    }
    return render(request, 'accounts/profile.html', context=context)