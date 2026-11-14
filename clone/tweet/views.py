from django.shortcuts import render
from . import models
from .forms import TweetForm , UserRegistrationForm
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login
# Create your views here.
def index(request):
    return render(request, 'index.html')

def tweet_list(request):
    tweets = models.Tweet.objects.all().order_by('-created_at')
    return render(request, 'tweet_list.html', {'tweets': tweets})

@login_required
def create_tweet(request):
    if request.method == 'POST':
        form = TweetForm(request.POST, request.FILES)
        if form.is_valid():
            tweet = form.save(commit=False)
            tweet.user = request.user
            tweet.save()
            return redirect('tweet_list')
    else:
        form = TweetForm()
    return render(request, 'tweet_edit.html', {'form': form})

@login_required
def tweet_edit(request, tweet_id):
    tweet= get_object_or_404(models.Tweet, pk=tweet_id, user=request.user)
    
    if request.method == 'POST':
        form=TweetForm(request.POST, request.FILES, instance=tweet)
        if form.is_valid():
            tweet = form.save(commit=False)
            tweet.user = request.user
            tweet.save()
            return redirect('tweet_list')
    else:
        form=TweetForm(instance=tweet)
    return render(request, 'tweet_edit.html', {'form': form, 'tweet': tweet})

@login_required
def delete_tweet(request, tweet_id):
    tweet= get_object_or_404(models.Tweet, pk=tweet_id, user=request.user)
    if request.method =="POST":
        tweet.delete()
        return redirect('tweet_list')
    return render(request, 'delete_tweet.html', {'tweet': tweet})

def register(request):
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            # form.save() automatically handles hashing and saving the password securely
            user = form.save() 
            # Log the user in immediately using your aliased auth_login
            login(request, user)
            return redirect('tweet_list')
    else:
        form = UserRegistrationForm()    
    return render(request, 'registration/register.html', {'form': form})