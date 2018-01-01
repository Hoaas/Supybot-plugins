# coding=utf8
###
# Copyright (c) 2012, Terje Hoås
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#   * Redistributions of source code must retain the above copyright notice,
#     this list of conditions, and the following disclaimer.
#   * Redistributions in binary form must reproduce the above copyright notice,
#     this list of conditions, and the following disclaimer in the
#     documentation and/or other materials provided with the distribution.
#   * Neither the name of the author of this software nor the name of
#     contributors to this software may be used to endorse or promote products
#     derived from this software without specific prior written consent.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED.  IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

###

import sys
import json
import random
import urllib.parse
import datetime

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

import supybot.utils.minisix as minisix
pickle = minisix.pickle

#datadir = conf.supybot.directories.data()
filename = conf.supybot.directories.data.dirize('TraktTV.pickle')

if sys.version_info[0] < 3:
    from urllib import quote
    from urllib import urlencode
    from urllib2 import HTTPError
else:
    from urllib.parse import quote
    from urllib.parse import urlencode
    from urllib.error import HTTPError

_ = PluginInternationalization('TraktTV')

pin_url = 'http://trakt.tv/pin/6010'
api_url = 'https://api.trakt.tv'

@internationalizeDocstring
class TraktTV(callbacks.Plugin):
    """Add the help for "@plugin help TraktTV" here
    This should describe *how* to use this plugin."""
    threaded = True

    def get_client_id(self):
        return self.registryValue('client_id')

    def get_client_secret(self):
        return self.registryValue('client_secret')

    def _convert_timestamp(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        age = datetime.datetime.now() - dt

        plural = lambda n: 's' if n > 1 else ''

        if age.days:
            age = '%s day%s ago' % (int(age.days), plural(age.days))
        elif age.seconds > 3600:
            hours = age.seconds / 3600
            age = '%s hour%s ago' % (int(hours), plural(hours))
        elif 60 <= age.seconds < 3600:
            minutes = age.seconds / 60
            age = '%s minute%s ago' % (int(minutes), plural(minutes))
        elif 30 < age.seconds < 60:
            age = 'less than a minute ago'
        else:
            age = 'less than %s second%s ago' % (int(d.seconds), plural(d.seconds))
        # str_dt = dt.strftime('%Y-%m-%d %I:%M %p')
        return age

    def get_access_token(self):
        pkl = None
        try:
            pkl = open(filename, 'rb')
        except IOError as e:
            self.log.debug('Unable to open pickled file: %s', e)
        if pkl:
           auth = pickle.load(pkl)
           self.log.debug('Auth from pickle-file: ' + str(auth))
        else:
            self.log.debug('No pickle file with access_token. Not previously logged in')
            return

        exp = auth.get('expires_in')
        created = auth.get('created_at')
        valid_time = created - exp
        now = datetime.datetime.timestamp(datetime.datetime.now())
        now = int(now)

        self.log.debug('Auth token valid for ' + str((now - valid_time)/(60*60*24)) + ' days.')
        self.log.debug('Auth token created at ' + str(datetime.datetime.fromtimestamp(created)))

        if (now - valid_time) < 60*60*24*60: # If validity is under 60 days, renew (it's valid for 90 days, so we renew on first use after a month)
            refresh_token = auth.get('refresh_token')
            auth = self.renew_access_token(refresh_token)

        access_token = auth.get('access_token')
        return access_token

    def renew_access_token(self, refresh_token):
        self.log.debug('Renewing token.')

        values = {
                'refresh_token': refresh_token,
                'client_id': self.get_client_id(),
                'client_secret': self.get_client_secret(),
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type': 'refresh_token'
            }

        headers = {
            'Content-Type': 'application/json'
        }

        token_url = api_url + '/oauth/token'

        response = utils.web.getUrl(token_url, headers=headers, data=json.dumps(values))
        response = response.decode()

        self.log.debug('Renew token response: ' + str(response))

        auth = json.loads(response)

        pkl = open(filename, 'wb')
        pickle.dump(auth, pkl)
        return auth

    def pin(self, irc, msg, args, pin):
        """<pin>
        Use to enter pin given by http://trakt.tv/pin/6010. Should only be needed initially, or if the plugin haven't been used in ~2 months. Other commands will give a warning if this is needed."""
        self.log.debug('Creating new access token.')
        values = {
                'code': pin,
                'client_id': self.get_client_id(),
                'client_secret': self.get_client_secret(),
                'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
                'grant_type': 'authorization_code'
            }
        headers = {
            'Content-Type': 'application/json'
        }

        token_url = api_url + '/oauth/token'

        self.log.debug('Accessing ' + token_url)
        self.log.debug(json.dumps(values))

        response = utils.web.getUrl(token_url, headers=headers, data=json.dumps(values))
        response = response.decode()

        auth = json.loads(response)

        self.log.debug('New auth: ' + str(auth))

        pkl = open(filename, 'wb')
        pickle.dump(auth, pkl)
        irc.replySuccess()
    pin = wrap(pin, ['text'])
        
    def np(self, irc, msg, args, nick):
        """[nick]

        Show currently playing movie/show from TraktTV. Needs to be a public
        profile. If no nick is supplied the IRC nick of the caller is attempted.""" 

        if not nick:
            nick = msg.nick

        url = api_url + '/users/%s/watching' % nick
        headers = {
            'Content-type' : 'application/json',
            'trakt-api-key' : self.get_client_id(),
            'trakt-api-version' : '2'
        }

        access_token = self.get_access_token()
        if access_token:
            headers['Authorization'] = 'Bearer ' + access_token

        try:
            self.log.debug('Trying ' + url + ' with these headers: ' + str(headers))
            data = utils.web.getUrl(url, headers=headers).decode()
        except utils.web.Error as err:
            if '404' in str(err):
                irc.error('User %s not found on Trakt.TV.' % nick)
                return
            if '401' in str(err):
                irc.error('Private account. Log in with an account that can see this person. Visit %s and type the pin you get into the supybot command TraktTV pin <pin> (e.g. !TraktTV pin 123ABC456))' % (pin_url))
                return
            irc.error(str(err))
            return
        if not data:
            irc.reply('Not currently scrobbling.')
            return
        try:
            data = json.loads(data)
        except:
            irc.error('Failed to parse response from trakt.tv.')
            raise
        if len(data) == 0:
            irc.error('Shouldn\'t really happen. Got an empty reply. But %s is probably not playing anything.' % nick)
            return
        
        show = data.get('show')
        if show:
            title = show.get('title')#.get('title')
            episode = data.get('episode')
            season = episode.get('season')
            ep_number = episode.get('number')
            ep_title = episode.get('title')
            output = '{4} np. {0} - {1} (s{2:02d}e{3:02d})'.format(
                ircutils.bold(title), ep_title, season, ep_number, nick
            )
            irc.reply(output)
            return
        movie = data.get('movie')
        if movie:
            title = movie.get('title')
            year = movie.get('year')
            output = '{2} np. {0} ({1})'.format(ircutils.bold(title), year, nick)
            irc.reply(output)
            return
        irc.error('Don\'t know what to do with this data. Not a show or a movie?')

    np = wrap(np, [optional('text')])

    @wrap(['text'])
    def random(self, irc, msg, args, show):
        """<show>
        
        Returns a random episode for a given show."""

        title, slug = self.search_by_title(show)

        url = '/shows/%s/seasons?extended=episodes' % slug

        data = self.apicall(url)

        random_season = random.choice(data).get('episodes')
        random_episode = random.choice(random_season)

        ep = random_episode

        output = 'Your random episode: %s - %s (s%02de%02d)' % (title, ep.get('title'), ep.get('season'), ep.get('number'))
        irc.reply(output)

    @wrap([('literal', ('movies', 'shows'))])
    def trending(self, irc, msg, args, type):
        """<movies|shows>
        Returns top 10 trending movies or shows."""

        url = '/%s/trending' % self.get_movie_show_url_part(type)
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows'))])
    def popular(self, irc, msg, args, type):
        """<movies|shows>
        Returns top 10 popular movies or shows."""

        url = '/%s/popular' % self.get_movie_show_url_part(type)
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def played(self, irc, msg, args, type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]
        Returns top 10 played movies or shows. Weekly by default."""

        type_part = self.get_movie_show_url_part(type)
        period_part = self.get_period_part(period)
        url = '/%s/played/%s' % (type_part, period_part)

        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def watched(self, irc, msg, args, type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]
        Returns top 10 watched movies or shows. Weekly by default."""

        type_part = self.get_movie_show_url_part(type)
        period_part = self.get_period_part(period)
        url = '/%s/watched/%s' % (type_part, period_part)
        
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def collected(self, irc, msg, args, type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]
        Returns top 10 collected movies or shows. Weekly by default."""

        type_part = self.get_movie_show_url_part(type)
        period_part = self.get_period_part(period)
        url = '/%s/collected/%s' % (type_part, period_part)
        
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows'))])
    def anticipated(self, irc, msg, args, type):
        """<movies|shows>
        Returns top 10 anticipated movies or shows."""

        url = '/%s/anticipated' % self.get_movie_show_url_part(type)
        
        irc.reply(self.get_lists(url))

    def get_movie_show_url_part(self, word):
        if word.startswith('m'):
            return 'movies'

        if word.startswith('s'):
            return 'shows'

    def get_period_part(self, period):
        if period is None or period.startswith('w'):
            return 'weekly'

        if period.startswith('d'):
            return 'daily'

        if period.startswith('m'):
            return 'monthly'

        if period.startswith('y'):
            return 'yearly'
    
    def get_lists(self, url):
        data = self.apicall(url)
        
        titles = []
        for item in data:
            m = item.get('movie')
            s = item.get('show')
            if m:
                x = m
            elif s:
                x = s
            else:
                x = item
            titles.append(x.get('title'))

        return ', '.join(titles)



    def apicall(self, url, client_id=True, auth_token=False):

        headers = {
            'Content-type': 'application/json',
            'trakt-api-version': '2'
        }

        if client_id:
            headers['trakt-api-key'] = self.get_client_id()

        if auth_token:
            access_token = self.get_access_token()
            if access_token:
                headers['Authorization'] = 'Bearer ' + access_token
            else:
                self.log.error('Error: TraktTV: Failed to get access token.')
                return
        
        url = api_url + url

        data = utils.web.getUrl(url, headers=headers).decode()
        data = json.loads(data)
        return data

    def search_by_title(self, search):
        url = '/search/show?query=%s' % urllib.parse.quote(search)
        
        data = self.apicall(url)

        show = data[0]
        title = show.get('show').get('title')
        slug = show.get('show').get('ids').get('slug')
        return title, slug

Class = TraktTV
