from django.contrib import admin
from django.urls import path, include

# Main URL patterns for the project
urlpatterns = [
    # Django admin interface
    path('admin/', admin.site.urls),
    
    # User authentication and management
    path('api/users/', include('accounts.urls')),
    path('api/data/', include('data.urls')),
]
