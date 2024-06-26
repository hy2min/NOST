from django.shortcuts import get_object_or_404, render
from openai import OpenAI
import requests
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from rest_framework import status
from .models import Book, Rating, Chapter
from .serializers import (
    BookSerializer,
    BookLikeSerializer,
    RatingSerializer,
    ChapterSerializer,
    ElementsSerializer,
)
from django.core import serializers
from django.core.files.base import ContentFile
from .generators import elements_generator, prologue_generator, summary_generator
from .deepL_translation import translate_summary


class BookListAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    # 전체 목록 조회
    def get(self, request):
        books = Book.objects.order_by("-created_at")
        serializer = BookSerializer(books, many=True)
        return Response(serializer.data)
    
    # 시놉시스 생성
    def post(self, request) :
        user_prompt = request.data.get("prompt")
        language = request.data.get("language", "EN-US")
        
        if not user_prompt:
            return Response(
                {"error": "Missing prompt"}, status=status.HTTP_400_BAD_REQUEST
            )
        
        # content 생성
        content = elements_generator(user_prompt)  # ai로 elements 생성
        translate_content = translate_summary(content, language)
        content["user_id"] = request.user.pk

        #image 생성
        client = OpenAI()
        response = client.images.generate(
            model="dall-e-3",
            prompt=f"{content['title']}, {content['tone']},{content['setting']}",
            size="1024x1024",
            quality="standard",
            n=1,
        )
        res = requests.get(response.data[0].url)
        image_content = ContentFile(res.content, name=f'{content['title']}.png')

        serializer = BookSerializer(data = content)
        if serializer.is_valid(raise_exception=True) :
            serializer.save(image = image_content)
            return Response(
                data={
                    "book_id": serializer.data["id"],
                    "content": translate_content,
                },  # FE에 content 응답
                status=status.HTTP_201_CREATED,
            )

class BookDetailAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        ratings = Rating.objects.filter(book=book)

        chapters = Chapter.objects.filter(book_id=book_id).order_by('chapter_num')
        chapter_serializer = ChapterSerializer(chapters, many=True)

        book_serializer = BookSerializer(book)

        response_data = book_serializer.data
        response_data["chapters"] = chapter_serializer.data
        return Response(response_data, status=200)


    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        if book.user_id != request.user:
            return Response({"error": "You don't have permission."}, status=status.HTTP_401_UNAUTHORIZED)

        language = request.data.get("language", "EN-US")
        selected_recommendation = request.data.get(
            "selected_recommendation", None)

        chapter = Chapter.objects.filter(book_id=book_id).last()
        elements = ElementsSerializer(book).data

        if not chapter:
            chapter_num = 0
            result = prologue_generator(elements)
            content = result["prologue"]
            content = translate_summary(content, language)

        else:
            if selected_recommendation:
                summary = f"{selected_recommendation['Title']}: {selected_recommendation['Description']}"
            else:
                summary = request.data.get("summary")
                if not summary:
                    return Response({"error": "Missing summary prompt"}, status=status.HTTP_400_BAD_REQUEST)

            chapter_num = chapter.chapter_num + 1
            prologue = Chapter.objects.filter(
                book_id=book_id, chapter_num=0).first()
            result = summary_generator(
                chapter_num, summary, elements, prologue.content if prologue else "", language
            )
            content = result["final_summary"]

        serializer = ChapterSerializer(
            data={"content": content, "book_id": book_id, "chapter_num": chapter_num}
        )
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            response_data = {
                "book_id": book_id,
                "translated_content": content,
                "chapter_num": chapter_num,
                "recommendations": result.get("recommendations", [])
            }
            return Response(data=response_data, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # 글 수정

    def put(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        if book.user_id != request.user:
            return Response(
                {"error": "You don't have permission."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        serializer = BookSerializer(book, data=request.data, partial=True)
        if serializer.is_valid(raise_exception=True):
            serializer.save()
            return Response(serializer.data, status=201)
        return Response(status=401)

    # 글 삭제
    def delete(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        if book.user_id != request.user:
            return Response(
                {"error": "You don't have permission."},
                status=status.HTTP_401_UNAUTHORIZED,
            )
        book.delete()
        return Response("No Content", status=204)


class DeletePrologueAPIView(APIView):
    def delete(self, request, book_id):
        prologue = Chapter.objects.filter(chapter_num=0, book_id=book_id)
        prologue.delete()
        return Response("Prologue deleted successfully", status=204)


class BookLikeAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        serializer = BookLikeSerializer(book)
        is_liked = book.is_liked.filter(id=request.user.id).exists()
        return Response(
            {
                "total_likes": book.total_likes(),
                "book": serializer.data,
                "like_bool": is_liked,
            },
            status=200,
        )

    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        if book.is_liked.filter(id=request.user.id).exists():
            book.is_liked.remove(request.user)
            like_bool = False
        else:
            book.is_liked.add(request.user)
            like_bool = True
        serializer = BookLikeSerializer(book)
        return Response(
            {
                "total_likes": book.total_likes(),
                "book": serializer.data,
                "like_bool": like_bool,
            },
            status=200,
        )


class UserLikedBooksAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        user = request.user
        book_likes = (
            user.book_likes.all()
        )  # 역참조를 이용해 사용자가 좋아요한 책 리스트를 가져옴
        serializer = BookSerializer(book_likes, many=True)
        return Response(serializer.data, status=200)


class UserBooksAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request):
        user = request.user
        user_books = (
            user.books.all()
        )  # 역참조를 이용해 사용자가 작성한 책 리스트를 가져옴
        serializer = BookSerializer(user_books, many=True)
        return Response(serializer.data, status=200)


class RatingAPIView(APIView):
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        user_rating = Rating.objects.filter(
            book=book, user_id=request.user.id).first()
        if user_rating:
            serializer = RatingSerializer(user_rating)
            return Response(serializer.data, status=200)
        return Response("User has not rated this book yet.", status=404)

    def post(self, request, book_id):
        book = get_object_or_404(Book, id=book_id)
        rating = request.data.get("rating")

        if rating not in [1, 2, 3, 4, 5]:
            return Response("Rating must be between 1 and 5", status=400)

        existing_rating = Rating.objects.filter(
            book=book, user_id=request.user
        ).exists()
        if existing_rating:
            return Response("You have already rated this book.", status=400)

        serializer = RatingSerializer(data={"rating": rating})
        if serializer.is_valid(raise_exception=True):
            serializer.save(user_id=request.user, book=book)
            return Response(serializer.data, status=200)
        return Response(status=400)

class BookImageAPIView(APIView) :
    permission_classes = [IsAuthenticatedOrReadOnly]

    def post(self, request, book_id):
        client = OpenAI()
        book = get_object_or_404(Book, id=book_id)
        response = client.images.generate(
            model="dall-e-2",
            prompt=f"{book.title}, {book.tone}",
            size="512x512",
            quality="standard",
            n=1,
        )
        res = requests.get(response.data[0].url)
        image_content = ContentFile(res.content, name=f'{book.title}.png')
        book.image.save(f'{book.title}.png', image_content)
