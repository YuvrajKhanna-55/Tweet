from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .api_views import (
    CommunityViewSet,
    ConversationViewSet,
    ProfileViewSet,
    TweetViewSet,
    csrf,
    login_view,
    logout_view,
    mark_notifications_read,
    notifications,
    register,
    session_user,
    users,
)

router = DefaultRouter()
router.register('tweets', TweetViewSet, basename='tweet-api')
router.register('profiles', ProfileViewSet, basename='profile-api')
router.register('conversations', ConversationViewSet, basename='conversation-api')
router.register('communities', CommunityViewSet, basename='community-api')

urlpatterns = [
    path('', include(router.urls)),
    path('auth/csrf/', csrf, name='api-csrf'),
    path('auth/me/', session_user, name='api-me'),
    path('auth/register/', register, name='api-register'),
    path('auth/login/', login_view, name='api-login'),
    path('auth/logout/', logout_view, name='api-logout'),
    path('notifications/', notifications, name='api-notifications'),
    path('notifications/read/', mark_notifications_read, name='api-notifications-read'),
    path('users/', users, name='api-users'),
]
