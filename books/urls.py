from django.urls import path
from . import views

urlpatterns = [
    path("", views.BookListAPIView.as_view()),
    path("<int:book_id>/", views.BookDetailAPIView.as_view()),
    path("<int:book_id>/del_prol/",views.DeletePrologueAPIView.as_view()),
    path("<int:book_id>/rating/", views.RatingAPIView.as_view()),
    path("<int:book_id>/like/", views.BookLikeAPIView.as_view()),
    path("<int:book_id>/image/", views.BookImageAPIView.as_view()),
    path("userlikedbooks/",views.UserLikedBooksAPIView.as_view()),
    path("userbooks/", views.UserBooksAPIView.as_view()),
]
