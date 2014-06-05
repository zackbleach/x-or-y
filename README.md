x-or-y
======

<p>Part of simple game based on the Twitter API that asks you to guess which account a tweet comes from.</p>

<p>This service provides an API which will return a random tweet from one of two specified users. To run
execute the command</p> 

<pre><code>python App.py</code></pre> 

<p>The app with then begin to run on <code> http://localhost:5000 </code> and you can submit a URL like this:
<code>http://localhost:5000?user1=firstTwitterUser&user2=secondTwitterUser</code> to grab a random tweet.

<p>To allow the app to access the Twitter API, create a file called 'twitter.cfg' in the root
of this project. It should contain your API Key, API Secret, Access Token & Access Token Secret. 
An example file is included in this repo.</p>

<p>I started this project because I wanted to learn about the [Flask microframework](http://flask.pocoo.org/) 
and Python. I'm still learning lots about both, so any feedback is hugely appreciated.</p>

The [front end](https://github.com/cham/x-or-y) for this was written by [@cham](http://twitter.com/cham)! 

A live version of the app can be found [here](http://x-or-y.zackblea.ch).

[Zack Bleach](http://zackblea.ch)
