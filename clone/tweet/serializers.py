import re
from pathlib import Path

from django.contrib.auth.models import User
from django.db.models import Count
from rest_framework import serializers

from .models import (
    Bookmark,
    Community,
    Conversation,
    Follow,
    Hashtag,
    Like,
    Notification,
    Profile,
    Repost,
    Message,
    MessageReaction,
    Tweet,
)


class UserSummarySerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'display_name', 'avatar']

    def get_display_name(self, obj):
        return getattr(getattr(obj, 'profile', None), 'display_name', '') or obj.username

    def get_avatar(self, obj):
        avatar = getattr(getattr(obj, 'profile', None), 'avatar', None)
        return avatar.url if avatar else None


class ProfileSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    followers_count = serializers.IntegerField(read_only=True)
    following_count = serializers.IntegerField(read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = Profile
        fields = [
            'user', 'display_name', 'bio', 'avatar', 'location', 'website',
            'created_at', 'followers_count', 'following_count', 'is_following',
        ]
        read_only_fields = ['created_at']

    def get_is_following(self, obj):
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated
            and Follow.objects.filter(follower=request.user, following=obj.user).exists()
        )


class TweetSerializer(serializers.ModelSerializer):
    user = UserSummarySerializer(read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)
    media = serializers.FileField(required=False, allow_null=True)
    like_count = serializers.IntegerField(read_only=True)
    reply_count = serializers.IntegerField(read_only=True)
    repost_count = serializers.IntegerField(read_only=True)
    bookmark_count = serializers.IntegerField(read_only=True)
    liked = serializers.SerializerMethodField()
    bookmarked = serializers.SerializerMethodField()
    reposted = serializers.SerializerMethodField()
    hashtags = serializers.SlugRelatedField(many=True, read_only=True, slug_field='name')
    mentions = UserSummarySerializer(many=True, read_only=True)
    quote_of = serializers.PrimaryKeyRelatedField(
        queryset=Tweet.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Tweet
        fields = [
            'id', 'user', 'text', 'photo', 'media', 'parent', 'quote_of', 'community',
            'mentions', 'created_at', 'updated_at',
            'like_count', 'reply_count', 'repost_count', 'bookmark_count',
            'liked', 'bookmarked', 'reposted', 'hashtags',
        ]
        read_only_fields = ['user', 'parent', 'mentions', 'created_at', 'updated_at']

    def validate_media(self, value):
        allowed = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}
        if value and Path(value.name).suffix.lower() not in allowed:
            raise serializers.ValidationError('Use an image, GIF, MP4, WebM, or MOV file.')
        return value

    def _has_relation(self, model, obj):
        request = self.context.get('request')
        return bool(
            request and request.user.is_authenticated
            and model.objects.filter(user=request.user, tweet=obj).exists()
        )

    def get_liked(self, obj):
        return self._has_relation(Like, obj)

    def get_bookmarked(self, obj):
        return self._has_relation(Bookmark, obj)

    def get_reposted(self, obj):
        return self._has_relation(Repost, obj)


class RegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Profile.objects.create(user=user, display_name=user.username)
        return user


class NotificationSerializer(serializers.ModelSerializer):
    actor = UserSummarySerializer(read_only=True)
    tweet = TweetSerializer(read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'actor', 'kind', 'tweet', 'is_read', 'created_at']


def update_hashtags(tweet):
    names = {name.lower() for name in re.findall(r'#([A-Za-z0-9_]+)', tweet.text)}
    hashtags = [Hashtag.objects.get_or_create(name=name)[0] for name in names]
    tweet.hashtags.set(hashtags)
    usernames = {name.lower() for name in re.findall(r'@([A-Za-z0-9_@.-]+)', tweet.text)}
    tweet.mentions.set(User.objects.filter(username__in=usernames))


class MessageSerializer(serializers.ModelSerializer):
    sender = UserSummarySerializer(read_only=True)
    photo = serializers.ImageField(required=False, allow_null=True)
    attachment = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'text', 'photo', 'attachment', 'created_at']
        read_only_fields = ['conversation', 'sender', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    participants = UserSummarySerializer(many=True, read_only=True)
    last_message = serializers.SerializerMethodField()

    class Meta:
        model = Conversation
        fields = ['id', 'name', 'is_group', 'participants', 'last_message', 'created_at']

    def get_last_message(self, obj):
        message = obj.messages.select_related('sender').last()
        return MessageSerializer(message, context=self.context).data if message else None


class CommunitySerializer(serializers.ModelSerializer):
    owner = UserSummarySerializer(read_only=True)
    members_count = serializers.IntegerField(read_only=True)
    is_member = serializers.SerializerMethodField()

    class Meta:
        model = Community
        fields = ['id', 'name', 'slug', 'description', 'owner', 'members_count', 'is_member', 'created_at']
        read_only_fields = ['owner', 'slug', 'created_at']

    def get_is_member(self, obj):
        request = self.context.get('request')
        return bool(request and request.user.is_authenticated and obj.members.filter(pk=request.user.pk).exists())
