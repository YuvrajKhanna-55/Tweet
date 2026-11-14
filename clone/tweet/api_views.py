from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils.text import slugify
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.views.decorators.csrf import ensure_csrf_cookie
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response

from .models import (
    Bookmark,
    Community,
    Conversation,
    Follow,
    Like,
    Message,
    MessageReaction,
    Notification,
    Profile,
    Repost,
    Tweet,
)
from .serializers import (
    CommunitySerializer,
    ConversationSerializer,
    MessageSerializer,
    NotificationSerializer,
    ProfileSerializer,
    RegistrationSerializer,
    TweetSerializer,
    UserSummarySerializer,
    update_hashtags,
)


def tweet_queryset():
    return Tweet.objects.select_related('user', 'user__profile').annotate(
        like_count=Count('likes', distinct=True),
        reply_count=Count('replies', distinct=True),
        repost_count=Count('reposts', distinct=True),
        bookmark_count=Count('bookmarks', distinct=True),
        engagement_score=Count('likes', distinct=True) + Count('replies', distinct=True) * 2
        + Count('reposts', distinct=True) * 2,
    ).order_by('-created_at')


@ensure_csrf_cookie
def csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
def session_user(request):
    if not request.user.is_authenticated:
        return Response({'user': None})
    Profile.objects.get_or_create(user=request.user, defaults={'display_name': request.user.username})
    return Response(UserSummarySerializer(request.user, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    serializer = RegistrationSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    user = serializer.save()
    login(request, user)
    return Response(
        UserSummarySerializer(user, context={'request': request}).data,
        status=status.HTTP_201_CREATED,
    )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login_view(request):
    user = authenticate(
        request,
        username=request.data.get('username', ''),
        password=request.data.get('password', ''),
    )
    if user is None:
        return Response({'detail': 'Invalid username or password.'}, status=status.HTTP_400_BAD_REQUEST)
    login(request, user)
    return Response(UserSummarySerializer(user, context={'request': request}).data)


@api_view(['POST'])
def logout_view(request):
    logout(request)
    return Response(status=status.HTTP_204_NO_CONTENT)


class TweetViewSet(viewsets.ModelViewSet):
    serializer_class = TweetSerializer

    def get_queryset(self):
        queryset = tweet_queryset()
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(text__icontains=search) | Q(user__username__icontains=search))
        if self.action in {'list', 'feed', 'following', 'bookmarks'}:
            queryset = queryset.filter(parent__isnull=True)
        if self.action in {'feed', 'following'} and self.request.user.is_authenticated:
            followed = Follow.objects.filter(follower=self.request.user).values('following_id')
            queryset = queryset.filter(Q(user=self.request.user) | Q(user_id__in=followed))
        if self.action == 'bookmarks':
            if not self.request.user.is_authenticated:
                return queryset.none()
            queryset = queryset.filter(bookmarks__user=self.request.user)
        if self.action == 'list':
            queryset = queryset.order_by('-engagement_score', '-created_at')
        return queryset.distinct()

    def perform_create(self, serializer):
        tweet = serializer.save(user=self.request.user)
        update_hashtags(tweet)

    def perform_update(self, serializer):
        if self.get_object().user != self.request.user:
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied('You can only edit your own tweets.')
        tweet = serializer.save()
        update_hashtags(tweet)

    def destroy(self, request, *args, **kwargs):
        tweet = self.get_object()
        if tweet.user != request.user:
            return Response({'detail': 'You can only delete your own tweets.'}, status=status.HTTP_403_FORBIDDEN)
        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=['get'])
    def feed(self, request):
        return self.list(request)

    @action(detail=False, methods=['get'])
    def following(self, request):
        if not request.user.is_authenticated:
            return Response({'detail': 'Login required.'}, status=status.HTTP_401_UNAUTHORIZED)
        return self.list(request)

    @action(detail=False, methods=['get'])
    def bookmarks(self, request):
        return self.list(request)

    @action(detail=True, methods=['post', 'delete'])
    def like(self, request, pk=None):
        tweet = self.get_object()
        relation, created = Like.objects.get_or_create(user=request.user, tweet=tweet)
        if request.method == 'DELETE':
            relation.delete()
        elif created and tweet.user != request.user:
            Notification.objects.create(recipient=tweet.user, actor=request.user, kind='like', tweet=tweet)
        return Response({'liked': request.method != 'DELETE'})

    @action(detail=True, methods=['post', 'delete'])
    def bookmark(self, request, pk=None):
        tweet = self.get_object()
        relation, _ = Bookmark.objects.get_or_create(user=request.user, tweet=tweet)
        if request.method == 'DELETE':
            relation.delete()
        return Response({'bookmarked': request.method != 'DELETE'})

    @action(detail=True, methods=['post', 'delete'])
    def repost(self, request, pk=None):
        tweet = self.get_object()
        relation, created = Repost.objects.get_or_create(user=request.user, tweet=tweet)
        if request.method == 'DELETE':
            relation.delete()
        elif created and tweet.user != request.user:
            Notification.objects.create(recipient=tweet.user, actor=request.user, kind='repost', tweet=tweet)
        return Response({'reposted': request.method != 'DELETE'})

    @action(detail=True, methods=['post'])
    def reply(self, request, pk=None):
        parent = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reply = serializer.save(user=request.user, parent=parent)
        update_hashtags(reply)
        if parent.user != request.user:
            Notification.objects.create(recipient=parent.user, actor=request.user, kind='reply', tweet=reply)
        return Response(self.get_serializer(reply).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def quote(self, request, pk=None):
        original = self.get_object()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        quote = serializer.save(user=request.user, quote_of=original)
        update_hashtags(quote)
        return Response(self.get_serializer(quote).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def replies(self, request, pk=None):
        tweet = self.get_object()
        replies = tweet.replies.select_related('user', 'user__profile').annotate(
            like_count=Count('likes', distinct=True),
            reply_count=Count('replies', distinct=True),
            repost_count=Count('reposts', distinct=True),
            bookmark_count=Count('bookmarks', distinct=True),
        ).order_by('created_at')
        return Response(self.get_serializer(replies, many=True).data)


class ProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    lookup_field = 'user__username'

    def get_queryset(self):
        return Profile.objects.select_related('user').annotate(
            followers_count=Count('user__followers', distinct=True),
            following_count=Count('user__following', distinct=True),
        )

    def retrieve(self, request, *args, **kwargs):
        username = kwargs.get('user__username')
        profile_user = get_object_or_404(User, username=username)
        profile, _ = Profile.objects.get_or_create(
            user=profile_user,
            defaults={'display_name': profile_user.username},
        )
        profile = self.get_queryset().get(pk=profile.pk)
        return Response(self.get_serializer(profile).data)

    @action(detail=True, methods=['post', 'delete'])
    def follow(self, request, **kwargs):
        profile = self.get_object()
        if profile.user == request.user:
            return Response({'detail': 'You cannot follow yourself.'}, status=status.HTTP_400_BAD_REQUEST)
        relation, created = Follow.objects.get_or_create(follower=request.user, following=profile.user)
        if request.method == 'DELETE':
            relation.delete()
        elif created:
            Notification.objects.create(recipient=profile.user, actor=request.user, kind='follow')
        return Response({'following': request.method != 'DELETE'})

    @action(detail=True, methods=['patch'])
    def edit(self, request, **kwargs):
        profile = self.get_object()
        if profile.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


class ConversationViewSet(viewsets.ModelViewSet):
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(participants=self.request.user).prefetch_related(
            'participants', 'messages__sender'
        ).distinct()

    def create(self, request, *args, **kwargs):
        usernames = request.data.get('usernames', [])
        participants = list(User.objects.filter(username__in=usernames))
        if not participants:
            return Response(
                {'detail': 'Enter an existing username to start a conversation.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if request.user not in participants:
            participants.append(request.user)
        is_group = len(participants) > 2
        if not is_group and len(participants) == 2:
            existing = Conversation.objects.filter(
                is_group=False, participants=request.user
            ).filter(participants=participants[0]).first()
            if existing:
                return Response(self.get_serializer(existing).data)
        conversation = Conversation.objects.create(
            name=request.data.get('name', ''),
            is_group=is_group,
        )
        conversation.participants.set(participants)
        return Response(self.get_serializer(conversation).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def messages(self, request, pk=None):
        conversation = self.get_object()
        serializer = MessageSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        message = serializer.save(conversation=conversation, sender=request.user)
        return Response(MessageSerializer(message, context={'request': request}).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        conversation = self.get_object()
        return Response(MessageSerializer(
            conversation.messages.select_related('sender'),
            many=True,
            context={'request': request},
        ).data)

    @action(detail=True, methods=['post'])
    def react(self, request, pk=None):
        conversation = self.get_object()
        message = get_object_or_404(
            Message,
            pk=request.data.get('message_id'),
            conversation=conversation,
        )
        emoji = request.data.get('emoji', '👍')[:16]
        reaction, created = MessageReaction.objects.get_or_create(
            message=message,
            user=request.user,
            emoji=emoji,
        )
        if not created:
            reaction.delete()
        return Response({'reacted': created, 'emoji': emoji})


class CommunityViewSet(viewsets.ModelViewSet):
    serializer_class = CommunitySerializer

    def get_queryset(self):
        queryset = Community.objects.select_related('owner').annotate(
            members_count=Count('members', distinct=True),
        )
        search = self.request.query_params.get('search', '').strip()
        if search:
            queryset = queryset.filter(Q(name__icontains=search) | Q(description__icontains=search))
        return queryset

    def perform_create(self, serializer):
        name = serializer.validated_data['name']
        community = serializer.save(
            owner=self.request.user,
            slug=slugify(name),
        )
        community.members.add(self.request.user)

    @action(detail=True, methods=['post', 'delete'])
    def membership(self, request, pk=None):
        community = self.get_object()
        if request.method == 'POST':
            community.members.add(request.user)
        else:
            community.members.remove(request.user)
        return Response({'is_member': request.method == 'POST'})


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def notifications(request):
    queryset = Notification.objects.filter(recipient=request.user).select_related(
        'actor', 'actor__profile', 'tweet', 'tweet__user'
    )
    return Response(NotificationSerializer(queryset[:50], many=True, context={'request': request}).data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def mark_notifications_read(request):
    Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
    return Response({'ok': True})


@api_view(['GET'])
def users(request):
    query = request.query_params.get('search', '').strip()
    queryset = User.objects.filter(is_active=True)
    if query:
        queryset = queryset.filter(Q(username__icontains=query) | Q(profile__display_name__icontains=query))
    return Response(UserSummarySerializer(queryset[:20], many=True, context={'request': request}).data)
