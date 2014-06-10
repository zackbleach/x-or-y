import random
import re
import datetime

import tweepy
from tweepy import Cursor
from threading import Thread

from flask import Flask, request
from flask.ext.runner import Runner

from flask.ext.jsonpify import jsonify
from flask_sillywalk import SwaggerApiRegistry, ApiParameter, ApiErrorResponse
import pylru

from config import Config

app = Flask(__name__)
app.debug = True
config = Config()

runner = Runner(app)

auth = tweepy.OAuthHandler(config.GetConsumerKey(), config.GetConsumerSecret())
auth.set_access_token(config.GetAccessKey(), config.GetAccessSecret())

api = tweepy.API(auth)

registry = SwaggerApiRegistry(
    app,
    baseurl=config.GetBaseUrl(),
    api_version="2.0",
    api_descriptions={"x-or-y": "Simple Twitter Game"})
register = registry.register
registerModel = registry.registerModel

USER1_URL_PARAM = 'user1'
USER2_URL_PARAM = 'user2'

timeline_cache = pylru.lrucache(1000)
user_cache = pylru.lrucache(1000)


class InvalidUsage(Exception):
    status_code = 400

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        returned_view = dict(self.payload or ())
        returned_view['statusCode'] = self.status_code
        returned_view['message'] = self.message
        return returned_view


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


def check_params(request):
    user1 = request.args.get(USER1_URL_PARAM)
    user2 = request.args.get(USER2_URL_PARAM)
    if not user1 or not user2:
        raise InvalidUsage('''You must specify user1 and user2 url params''')


def get_tweets_for_user(user_name):
    tweets = []
    for status in Cursor(api.user_timeline, screen_name=user_name,
                         include_rts=False).items(10):
        tweets.append(status)
    thread = Thread(target=fill_cache, args=(user_name, ))
    thread.start()
    user_cache[status.user.screen_name.lower()] = status.user
    return tweets


def fill_cache(user_name):
    print 'filling cache'
    count = 0
    for status in Cursor(api.user_timeline, screen_name=user_name,
                         include_rts=False).items(100):
        timeline_cache[user_name].append(status)
        count += 1
    print 'filled cache with ' + str(count) + 'items'


def get_tweets_from_cache(user):
    if user in timeline_cache:
        return timeline_cache[user]
    else:
        tweets = get_tweets_for_user(user)
        timeline_cache[user] = tweets
        return tweets


def is_user_name(word):
    twitter_username_re = re.compile(r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+'
                                     '[A-Za-z0-9]+)')
    return re.search(twitter_username_re, word)


def remove_usernames(tweet):
    cleaned_text = ''
    for word in tweet.text.split(" "):
        if is_user_name(word):
            word = '@[redacted]'
        cleaned_text += word + ' '
    tweet.text = cleaned_text
    return tweet


def remove_urls(tweet):
    url_re = re.compile(r'(?P<url>https?://[^\s]+)')
    tweet.text = re.sub(url_re, ' ', tweet.text)
    return tweet


def get_user_names(request):
    user1 = request.args.get(USER1_URL_PARAM)
    user2 = request.args.get(USER2_URL_PARAM)
    return user1, user2


def get_random_tweet(user1, user2):
    time = datetime.datetime.now()
    tweets = []
    tweets.extend(get_tweets_from_cache(user1))
    tweets.extend(get_tweets_from_cache(user2))
    print (datetime.datetime.now() - time)
    return random.choice(tweets)


@register('/api/tweet',
          method='GET',
          nickname="I Guess",
          parameters=[
              ApiParameter(
                  name="user1",
                  description="First user to collect random tweets from",
                  required=True,
                  dataType="str",
                  paramType="query",
                  allowMultiple=False),
              ApiParameter(
                  name="user2",
                  description="Second user to collect random tweets from",
                  required=True,
                  dataType="str",
                  paramType="query",
                  allowMultiple=False)
              ],
          responseMessages=[
              ApiErrorResponse(400, "Could not collect tweets from user")
              ])
def get_tweet():
    check_params(request)
    user1, user2 = get_user_names(request)
    tweet = get_random_tweet(user1, user2)
    tweet = remove_usernames(tweet)
    tweet = remove_urls(tweet)
    user_one = user_cache[user1.lower()]
    user_two = user_cache[user2.lower()]
    return jsonify(id=tweet.id,
                   tweet=tweet.text,
                   userOne=user_one.profile_image_url,
                   userTwo=user_two.profile_image_url,
                   thisUser=int(user_one.id != tweet.user.id)+1)


if __name__ == '__main__':
    runner.run()
