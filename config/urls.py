from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),

    path(
        'api/accounts/',
        include('accounts.urls')
    ),
    path('api/wallets/', include('wallets.urls')),
    path("api/businesses/", include("businesses.urls")),
    path("api/cards/", include("cards.urls")),
]