from django.db.models import Avg
from rest_framework import serializers
from .models import Book, Chapter, Rating

class ChapterSerializer(serializers.ModelSerializer):
    class Meta:
        model = Chapter
        fields = "__all__"

class BookSerializer(serializers.ModelSerializer):
    average_rating = serializers.SerializerMethodField()
    user_nickname = serializers.SerializerMethodField()
    chapters = ChapterSerializer(many=True, read_only=True)

    class Meta:
        model = Book
        fields = "__all__"

    def get_average_rating(self, book):
        avg_rating = Rating.objects.filter(book=book).aggregate(avg_rating=Avg("rating"))["avg_rating"]
        return round(avg_rating, 1) if avg_rating is not None else None

    def get_user_nickname(self, book):
        return book.user_id.nickname

    def get_chapters(self,book) :
        return book.full_text.content
    
    def get_image_url(self,obj) :
        request = self.context.get('request')
        if obj.image : 
            return request.build_absolute_uri(obj.image.url)
        return None

class BookLikeSerializer(BookSerializer):
    total_likes = serializers.IntegerField(read_only=True)


class RatingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rating
        fields = "__all__"
        read_only_fields = ("book", "user_id")


class ElementsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = (
            "title",
            "genre",
            "theme",
            "tone",
            "setting",
            "characters",
        )
