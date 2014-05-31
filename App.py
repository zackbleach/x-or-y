from twitter import Twitter, OAuth, TwitterHTTPError

from flask import Flask
from flask import request
from flask import jsonify

import random
import pylru
import re

app = Flask(__name__)
app.debug = True

# strip out @mentions and user names (spell checker for user names) ?

OAUTH_TOKEN = '18120137-S6OHWrpcXSeaD9HdEYTZBM9H0IBx4SVxZfSctVlCj'
OAUTH_SECRET = '2lLI9wFbo3D3asRuPmUXx5vOXMIWoOwijzUhETmq4XZGk'
CONSUMER_SECRET = 'qu8NO9wLTF7S42ggR83hiWQMxmc287rB15PRZV6wcIemmiZUiS'
CONSUMER_KEY = '8sd5ORXMz4cucnqLtrYjf3Mbg'

CACHE_SIZE = 30
tweets_cache = cache = pylru.lrucache(CACHE_SIZE)

TWITTER_USERNAME_RE = re.compile(r'(?<=^|(?<=[^a-zA-Z0-9-_\.]))@([A-Za-z]+'
                                 '[A-Za-z0-9]+)')

twitter = Twitter(auth=OAuth(OAUTH_TOKEN, OAUTH_SECRET,
                  CONSUMER_KEY, CONSUMER_SECRET))


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


def get_tweets_for_user(user_name):
    try:
        return twitter.statuses.user_timeline(screen_name=user_name)
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
    user1 = request.args.get('user1')
    user2 = request.args.get('user2')
    if not user1 or not user2:
        raise InvalidUsage('''You must specify user1 and user2 url params''')


@app.errorhandler(InvalidUsage)
def handle_invalid_usage(error):
    response = jsonify(error.to_dict())
    response.status_code = error.status_code
    return response


@app.route('/')
def main():
    check_params(request)
    user_one = request.args.get('user1')
    user_two = request.args.get('user2')
    user_one_tweets = get_tweets_from_cache(user_one)
    user_two_tweets = get_tweets_from_cache(user_two)
    tweets = []
    tweets.append(random.choice(user_one_tweets)['text'])
    tweets.append(random.choice(user_two_tweets)['text'])
    randNo = random.randint(0, 1)
    tweet = tweets[randNo]
    new_tweet = ''
    for s in tweet.split(" "):
        if s.startswith("RT"):
            continue
        if re.search(TWITTER_USERNAME_RE, s):
            s = '@[redacted]'
        new_tweet += s + ' '
    return jsonify(tweet=new_tweet, user_id=str(randNo+1))

if __name__ == '__main__':
    app.run()
