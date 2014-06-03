import hashlib
import random
import re

from flask import Flask, request
from flask.ext.jsonpify import jsonify
from flask_sillywalk import SwaggerApiRegistry, ApiParameter, ApiErrorResponse
from twitter import Twitter, OAuth, TwitterHTTPError
import pylru

from config import Config

app = Flask(__name__)
app.debug = True
config = Config()

twitter = Twitter(auth=OAuth(config.GetAccessKey(),
                             config.GetAccessSecret(),
                             config.GetConsumerKey(),
                             config.GetConsumerSecret()))

registry = SwaggerApiRegistry(
    app,
    baseurl=config.GetBaseUrl(),
    api_version="1.0",
    api_descriptions={"x-or-y": "Simple Twitter Game"})
register = registry.register
registerModel = registry.registerModel

USER1_URL_PARAM = 'user1'
USER2_URL_PARAM = 'user2'

timeline_cache = pylru.lrucache(1000)
user_tweet_cache = pylru.lrucache(1000)
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


def get_tweets_for_user(user_name):
    try:
        timeline = twitter.statuses.user_timeline(screen_name=user_name,
                                                  include_rts=False)
        username = timeline[0]['user']['screen_name'].lower()
        user_cache[username] = timeline[0]['user']
        return timeline
    except TwitterHTTPError as twitter_error:
        error_message = 'Error recieving tweets for user: %s' % user_name
        error_code = twitter_error.e.code
        raise InvalidUsage(error_message,
                           status_code=error_code)


def get_user(username):
    return twitter.users.lookup(screen_name=username)


def get_tweets_from_cache(user):
    if user in timeline_cache:
        return timeline_cache[user]
    else:
        tweets = get_tweets_for_user(user)
        timeline_cache[user] = tweets
        return tweets


def check_params(request):
    user1 = request.args.get(USER1_URL_PARAM)
    user2 = request.args.get(USER2_URL_PARAM)
    if not user1 or not user2:
        raise InvalidUsage('''You must specify user1 and user2 url params''')


def is_user_name(word):
    twitter_username_re = re.compile(r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+'
                                     '[A-Za-z0-9]+)')
    return re.search(twitter_username_re, word)


def remove_usernames(tweet):
    cleaned_text = ''
    for word in tweet['text'].split(" "):
        if is_user_name(word):
            word = '@[redacted]'
        cleaned_text += word + ' '
    tweet['text'] = cleaned_text
    return tweet


def get_random_tweet(user1, user2):
    tweets = []
    tweets.extend(get_tweets_from_cache(user1))
    tweets.extend(get_tweets_from_cache(user2))
    return random.choice(tweets)


@register('/x-or-y/api/answer',
          method='POST',
          nickname="I Guess",
          parameters=[
              ApiParameter(
                  name="tweetId",
                  description="ID of tweet to guess answer for",
                  required=True,
                  dataType="str",
                  paramType="json",
                  allowMultiple=False),
              ApiParameter(
                  name="answer",
                  description="User who you think posted the tweet",
                  required=True,
                  dataType="str",
                  paramType="json",
                  allowMultiple=False)
              ],
          responseMessages=[
              ApiErrorResponse(401, "Could not log in to Twitter: bad auth")
              ])
def check_answer():
    print 'getting answer'
    content = request.json
    print content
    tweet = request.json['tweetId']
    print tweet
    user = user_tweet_cache[tweet]
    print 'got user: ' + user
    if not tweet:
        print 'not tweet'
        raise InvalidUsage("Tweet does not exist",
                           status_code=400)
    answer = request.json['answer']
    print 'got answer: ' + answer
    correct = False
    if (answer == user):
        print 'correct'
        correct = True
    else:
        print 'incorrect'
    return jsonify(id=tweet, answer=answer,
                   correct=correct)


@register('/x-or-y/api/get-tweet',
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
              ApiErrorResponse(400, "Could not collect tweets from user"),
              ApiErrorResponse(401, "Could not log in to Twitter: bad auth")
              ])
def main():
    check_params(request)
    user1 = request.args.get(USER1_URL_PARAM)
    user2 = request.args.get(USER2_URL_PARAM)
    tweet = get_random_tweet(user1, user2)
    tweet_user = tweet['user']['screen_name'].lower()
    tweet = remove_usernames(tweet)
    md5 = hashlib.md5()
    md5.update(tweet_user+tweet['text'])
    tweet_id = md5.hexdigest()
    user_tweet_cache[tweet_id] = tweet_user
    userOne = user_cache[user1.lower()]
    userTwo = user_cache[user2.lower()]
    return jsonify(tweet=tweet['text'], id=tweet_id,
                   userOne=userOne, userTwo=userTwo)

if __name__ == '__main__':
    app.run()
