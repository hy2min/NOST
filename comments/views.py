from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated,IsAuthenticatedOrReadOnly
from rest_framework.response import Response
from rest_framework import status
from books.models import Book
from .models import Comment
from .serializers import CommentSerializer

class CommentListAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        comments = book.comments.all()
        serializer = CommentSerializer(comments, many=True)
        return Response(serializer.data)

    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        serializer = CommentSerializer(data=request.data)
        if serializer.is_valid(raise_exception=True):
            serializer.save(user_id=request.user, book=book)
            return Response(serializer.data, status=201)


class CommentDetailAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def put(self, request, book_id, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        if comment.user_id != request.user:
            return Response(
                {"error": "You don't have permission."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        serializer = CommentSerializer(
            comment, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data)

    def delete(self, request, book_id, comment_id):
        comment = get_object_or_404(Comment, id=comment_id)
        if comment.user_id != request.user:
            return Response(
                {"error": "You don't have permission."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        comment.delete()
        return Response("NO comment", status=204)
