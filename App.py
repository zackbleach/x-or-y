import random

import re
from flask import Flask, request, jsonify
from flask_sillywalk import SwaggerApiRegistry, ApiParameter, ApiErrorResponse
from twitter import Twitter, OAuth, TwitterHTTPError
import pylru
from flask_cors import cross_origin

from config import Config

app = Flask(__name__)

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

tweets_cache = cache = pylru.lrucache(30)


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
        return twitter.statuses.user_timeline(screen_name=user_name,
                                              include_rts=False)
    except TwitterHTTPError as twitter_error:
        error_message = 'Error recieving tweets for user: %s' % user_name
        error_code = twitter_error.e.code
        raise InvalidUsage(error_message,
                           status_code=error_code)


def get_tweets_from_cache(user):
    if user in tweets_cache:
        return tweets_cache[user]
    else:
        tweets = get_tweets_for_user(user)
        tweets_cache[user] = tweets
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


@register('/x-or-y/api/get-tweet',
          parameters=[
              ApiParameter(
                  name="user1",
                  description="First user",
                  required=True,
                  dataType="str",
                  paramType="query",
                  allowMultiple=False)
              ],
          responseMessages=[
              ApiErrorResponse(401, "Bad Auth")
              ])
@cross_origin()
def main():
    check_params(request)
    user1 = request.args.get(USER1_URL_PARAM)
    user2 = request.args.get(USER2_URL_PARAM)
    tweet = get_random_tweet(user1, user2)
    tweet = remove_usernames(tweet)
    return jsonify(tweet=tweet['text'], user=tweet['user']['screen_name'])

if __name__ == '__main__':
    app.run()
