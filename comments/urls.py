from django.urls import path, include
from . import views
urlpatterns = [
        path("<int:book_id>/", views.CommentListAPIView.as_view()),
    path(
        "<int:book_id>/<int:comment_id>/", views.CommentDetailAPIView.as_view()
    ),
]
