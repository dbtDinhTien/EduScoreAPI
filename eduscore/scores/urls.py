from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from . import views

r = DefaultRouter()
r.register('categories',views.CategoryViewSet, basename='category')
r.register('activities',views.ActivityViewSet, basename='activity')
r.register('class', views.ClassViewSet, basename='class')
r.register('department', views.DepartmentViewSet, basename='department')
r.register('users', views.UserViewSet, basename='user')
r.register('newsfeeds', views.NewsFeedViewSet, basename='newsfeed')
r.register('registration', views.RegistrationViewSet, basename='registration')
r.register('comments', views.CommentViewSet, basename='comment')
r.register('participation', views.ParticipationViewSet, basename='participation')
r.register('group', views.EvaluationGroupViewSet, basename='group')
r.register('criteria', views.EvaluationCriteriaViewSet, basename='criteria')
r.register('disciplined', views.DisciplinePointViewSet, basename='discipline')
r.register('report', views.ReportViewSet, basename='report')
r.register('message', views.MessageViewSet, basename='message')
r.register('stat', views.ScoreStatsViewSet, basename='stat')
r.register('csv', views.ExportCSVViewSet, basename='csv')
r.register('pdf', views.ExportPDFViewSet, basename='pdf')
urlpatterns = [
    path('',include(r.urls))
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)