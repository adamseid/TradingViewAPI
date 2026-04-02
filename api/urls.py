from django.urls import path
from api.views.token_views import home_page, token_detail, sync_tokens, sync_token_data, reset_in_use
from api.views.auth_views import register_user, login_user, logout_user, current_user
from api.views.wishlist_views import toggle_wishlist
from api.views.security_views import csrf_token

urlpatterns = [
    # csrf
    path("auth/csrf/", csrf_token, name="csrf_token"),

    # internal / cron / celery
    path("token/sync/", sync_tokens, name="token_sync"),
    path("token/sync-data/", sync_token_data, name="token_data_sync"),
    path("token/reset-in-use/", reset_in_use, name="reset_in_use"),

    # frontend
    path("", home_page, name="home_page"),
    path("token/<str:ticker>/", token_detail, name="token_detail"),
    path("token/wishlist/toggle/", toggle_wishlist, name="toggle_wishlist"),

    # Auth
    path("auth/register/", register_user, name="register_user"),
    path("auth/login/", login_user, name="login_user"),
    path("auth/logout/", logout_user, name="logout_user"),
    path("auth/me/", current_user, name="current_user"),
]