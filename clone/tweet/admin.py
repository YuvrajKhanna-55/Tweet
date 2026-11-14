from django.contrib import admin
from . import models

# Register your models here.
admin.site.register([
    models.Tweet,
    models.Profile,
    models.Follow,
    models.Like,
    models.Bookmark,
    models.Repost,
    models.Hashtag,
    models.Notification,
    models.Conversation,
    models.Message,
    models.MessageReaction,
    models.Community,
])
