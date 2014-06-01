import ConfigParser
import os


class Config(object):
    def __init__(self):
        self._config = None

    def GetConsumerKey(self):
        return self._GetTwitterOption('consumer_key')

    def GetConsumerSecret(self):
        return self._GetTwitterOption('consumer_secret')

    def GetAccessKey(self):
        return self._GetTwitterOption('access_key')

    def GetAccessSecret(self):
        return self._GetTwitterOption('access_secret')

    def GetBaseUrl(self):
        return self._GetSwaggerOption('base_url')

    def _GetTwitterOption(self, option):
        return self._GetOption('twitter_credentials', option)

    def _GetSwaggerOption(self, option):
        return self._GetOption('swagger', option)

    def _GetOption(self, section, option):
        try:
            return self._GetConfig().get(section, option)
        except:
            return None

    def _GetConfig(self):
        if not self._config:
            self._config = ConfigParser.ConfigParser()
            self._config.read(os.path.expanduser('x-or-y.cfg'))
        return self._config
