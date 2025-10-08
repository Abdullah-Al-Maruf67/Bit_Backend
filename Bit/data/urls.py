from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'repositories', views.RepositoryViewSet, basename='repository')
router.register(r'share-links', views.ShareableLinkViewSet, basename='share-link')
router.register(r'commits', views.CommitViewSet, basename='commit')

urlpatterns = [
    path('', include(router.urls)),
    path('repositories/<int:repository_id>/commits/<int:commit_id>/merge/', 
         views.merge_commit, 
         name='merge-commit'),
] 