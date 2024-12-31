from django.urls import path, include
from rest_framework.routers import DefaultRouter
from accounts.views import UserViewSet
from polls.views import PollViewSet, ChoiceViewSet, VoteViewSet

# Create a router and register our viewsets with it
router = DefaultRouter()

# Accounts URLs
router.register(r'users', UserViewSet, basename='user')

# Polls URLs
router.register(r'polls', PollViewSet, basename='poll')
router.register(r'choices', ChoiceViewSet, basename='choice')
router.register(r'votes', VoteViewSet, basename='vote')

# The API URLs are now determined automatically by the router
urlpatterns = [
    path('', include(router.urls)),
    path('api-auth/', include('rest_framework.urls')),  # For browsable API login/logout
] 