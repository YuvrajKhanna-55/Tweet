from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class Tweet(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    text= models.CharField(max_length=250)
    photo= models.ImageField(upload_to='tweet_photos/', blank=True, null=True)
    media = models.FileField(upload_to='tweet_media/', blank=True, null=True)
    parent = models.ForeignKey(
        'self',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='replies',
    )
    quote_of = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='quotes',
    )
    mentions = models.ManyToManyField(
        User,
        blank=True,
        related_name='mentioned_tweets',
    )
    community = models.ForeignKey(
        'Community',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='tweets',
    )
    created_at=models.DateTimeField(auto_now_add=True)
    updated_at= models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}: {self.text[:10]}"


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    display_name = models.CharField(max_length=80, blank=True)
    bio = models.CharField(max_length=160, blank=True)
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    location = models.CharField(max_length=100, blank=True)
    website = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.display_name or self.user.username


class Follow(models.Model):
    follower = models.ForeignKey(User, on_delete=models.CASCADE, related_name='following')
    following = models.ForeignKey(User, on_delete=models.CASCADE, related_name='followers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['follower', 'following'], name='unique_follow'),
            models.CheckConstraint(
                condition=~models.Q(follower=models.F('following')),
                name='cannot_follow_self',
            ),
        ]


class Like(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='likes')
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='likes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'tweet'], name='unique_like'),
        ]


class Bookmark(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmarks')
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='bookmarks')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'tweet'], name='unique_bookmark'),
        ]


class Repost(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reposts')
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, related_name='reposts')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'tweet'], name='unique_repost'),
        ]


class Hashtag(models.Model):
    name = models.CharField(max_length=100, unique=True)
    tweets = models.ManyToManyField(Tweet, related_name='hashtags', blank=True)


class Notification(models.Model):
    recipient = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    actor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_sent')
    kind = models.CharField(max_length=20)
    tweet = models.ForeignKey(Tweet, on_delete=models.CASCADE, null=True, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class Conversation(models.Model):
    participants = models.ManyToManyField(User, related_name='conversations')
    name = models.CharField(max_length=100, blank=True)
    is_group = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


class Message(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_messages')
    text = models.CharField(max_length=1000, blank=True)
    photo = models.ImageField(upload_to='message_photos/', blank=True, null=True)
    attachment = models.FileField(upload_to='message_media/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']


class MessageReaction(models.Model):
    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name='reactions')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    emoji = models.CharField(max_length=16)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['message', 'user', 'emoji'], name='unique_message_reaction'),
        ]


class Community(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.CharField(max_length=280, blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_communities')
    members = models.ManyToManyField(User, related_name='communities', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']