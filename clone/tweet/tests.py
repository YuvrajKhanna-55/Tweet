from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Community, Conversation, Follow, Like, Profile, Tweet

class SocialApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.alice = User.objects.create_user(username='alice', password='Password123!')
        self.bob = User.objects.create_user(username='bob', password='Password123!')
        Profile.objects.create(user=self.alice, display_name='Alice')
        Profile.objects.create(user=self.bob, display_name='Bob')

    def login(self, user):
        self.client.force_authenticate(user=user)

    def test_registration_creates_profile_and_session(self):
        response = self.client.post('/api/auth/register/', {
            'username': 'charlie',
            'email': 'charlie@example.com',
            'password': 'Password123!',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Profile.objects.filter(user__username='charlie').exists())

    def test_users_only_see_personalized_feed(self):
        Tweet.objects.create(user=self.alice, text='Alice post')
        Tweet.objects.create(user=self.bob, text='Bob post')
        self.login(self.alice)
        response = self.client.get('/api/tweets/feed/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

        Follow.objects.create(follower=self.alice, following=self.bob)
        response = self.client.get('/api/tweets/feed/')
        self.assertEqual(len(response.data['results']), 2)

    def test_public_feed_is_available_without_login(self):
        Tweet.objects.create(user=self.alice, text='Public post')
        response = self.client.get('/api/tweets/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 1)

    def test_like_is_unique_and_toggleable(self):
        tweet = Tweet.objects.create(user=self.alice, text='Like me')
        self.login(self.bob)
        self.assertEqual(self.client.post(f'/api/tweets/{tweet.id}/like/').status_code, 200)
        self.assertEqual(self.client.post(f'/api/tweets/{tweet.id}/like/').status_code, 200)
        self.assertEqual(Like.objects.filter(user=self.bob, tweet=tweet).count(), 1)
        self.assertEqual(self.client.delete(f'/api/tweets/{tweet.id}/like/').status_code, 200)
        self.assertFalse(Like.objects.filter(user=self.bob, tweet=tweet).exists())

    def test_user_cannot_edit_another_users_tweet(self):
        tweet = Tweet.objects.create(user=self.alice, text='Protected')
        self.login(self.bob)
        response = self.client.patch(f'/api/tweets/{tweet.id}/', {'text': 'Changed'})
        self.assertEqual(response.status_code, 403)

    def test_following_feed_and_profile_edit_work(self):
        Tweet.objects.create(user=self.alice, text='Alice post')
        self.login(self.bob)
        response = self.client.get('/api/tweets/following/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['results']), 0)
        self.assertEqual(self.client.post('/api/profiles/alice/follow/').status_code, 200)
        response = self.client.get('/api/tweets/following/')
        self.assertEqual(len(response.data['results']), 1)

        self.login(self.alice)
        response = self.client.patch('/api/profiles/alice/edit/', {'bio': 'Building in public'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['bio'], 'Building in public')
        response = self.client.patch(
            '/api/profiles/alice/edit/',
            {'display_name': 'Alice Builder', 'location': 'Earth'},
            format='multipart',
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['display_name'], 'Alice Builder')

    def test_authenticated_user_can_create_community(self):
        self.login(self.alice)
        response = self.client.post('/api/communities/', {
            'name': 'Django Builders',
            'description': 'A place for Django builders.',
        })
        self.assertEqual(response.status_code, 201)
        self.assertTrue(Community.objects.filter(slug='django-builders', members=self.alice).exists())

    def test_users_can_create_conversation_and_send_message(self):
        self.login(self.alice)
        response = self.client.post('/api/conversations/', {'usernames': ['bob']}, format='json')
        self.assertEqual(response.status_code, 201)
        conversation = Conversation.objects.get(pk=response.data['id'])
        response = self.client.post(
            f'/api/conversations/{conversation.id}/messages/',
            {'text': 'Hello Bob'},
            format='json',
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['text'], 'Hello Bob')

    def test_post_detail_returns_replies(self):
        post = Tweet.objects.create(user=self.alice, text='Parent')
        Tweet.objects.create(user=self.bob, text='Reply', parent=post)
        timeline = self.client.get('/api/tweets/')
        self.assertEqual(len(timeline.data['results']), 1)
        response = self.client.get(f'/api/tweets/{post.id}/replies/')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
