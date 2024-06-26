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
import time
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

    def auth(self, irc):
        self.log.debug('Creating new access token.')
        values = {
                'client_id': self.get_client_id()
        }
        headers = {
            'Content-Type': 'application/json'
        }

        codes_url = api_url + '/oauth/device/code'

        self.log.debug('Accessing ' + codes_url)
        self.log.debug(json.dumps(values))

        response = utils.web.getUrl(codes_url, headers=headers, data=json.dumps(values))
        response = response.decode()

        codes = json.loads(response)

        self.log.debug('Codes response: ' + str(codes))
        irc.reply('Visit %s and input %s.'% (codes.get('verification_url'), codes.get('user_code')))

        token_url = api_url + '/oauth/device/token'
        authed = False
        interval = codes.get('interval')
        time_max = codes.get('expires_in')
        time_expired = 0

        values = {
                'client_id': self.get_client_id(),
                'client_secret': self.get_client_secret(),
                'code': codes.get('device_code')
        }


        auth = None
        while (not authed and time_expired < time_max):
            time.sleep(interval)
            time_expired += interval
            time_max = 30
            self.log.info('Time expired: ' + str(time_expired))

            try:
                response = utils.web.getUrl(token_url, headers=headers, data=json.dumps(values))
            except utils.web.Error as err:
                if '400' in str(err): # Pending - waiting for user to authorize your app
                    continue
                if '404' in str(err): # Not Found - invalid device_code
                    irc.error('Not Found - invalid device_code. Report a bug at https://github.com/Hoaas/Supybot-plugins/issues/new?title=TraktTV:%20Invalid%20device_code')
                    return
                if '409' in str(err): # Already Used - user already approved this code
                    irc.error('This code is already used. Try again?')
                    return
                if '410' in str(err): # Expired - the tokens have expired, restart the process
                    irc.error('The tokens have expired. Try again?')
                    return
                if '418' in str(err): # Denied - user explicitly denied this code
                    irc.error('You have to press the other button! (the green one that says YES)')
                    return
                if '429' in str(err): # Slow Down - your app is polling too quickly
                    irc.error('Slow Down - your app is polling too quickly. Report a bug at https://github.com/Hoaas/Supybot-plugins/issues/new?title=TraktTV:%20429%20Slow%20Down')
                    return
                irc.error(str(err))
                return

            authed = True

            response = response.decode()

            self.log.debug('Response: ' + response)

            auth = json.loads(response)

        pkl = open(filename, 'wb')
        pickle.dump(auth, pkl)
        irc.reply('Authed!')

    @wrap([optional('text')])
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
                self.auth(irc)
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

    @wrap(['text'])
    def random(self, irc, msg, args, show):
        """<show>
        
        Returns a random episode for a given show."""

        title, slug = self.search_item_by_title_and_type(show, 'show')
        if (title is None or slug is None):
            irc.reply('Sorry, no hits.')
            return

        url = '/shows/%s/seasons?extended=episodes' % slug

        data = self.apicall(url)

        random_season = random.choice(data).get('episodes')
        random_episode = random.choice(random_season)

        ep = random_episode

        output = 'Your random episode: %s - %s (s%02de%02d)' % (title, ep.get('title'), ep.get('season'), ep.get('number'))
        irc.reply(output)

    @wrap([('literal', ('movies', 'shows'))])
    def trending(self, irc, msg, args, media_type):
        """<movies|shows>
        Returns top 10 trending movies or shows."""

        url = '/%s/trending' % media_type
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows'))])
    def popular(self, irc, msg, args, media_type):
        """<movies|shows>
        Returns top 10 popular movies or shows."""

        url = '/%s/popular' % media_type
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def played(self, irc, msg, args, media_type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]
        Returns top 10 played movies or shows. Weekly by default."""

        period_part = self.get_period_part(period)
        url = '/%s/played/%s' % (media_type, period_part)

        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def watched(self, irc, msg, args, media_type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]
        Returns top 10 watched movies or shows. Weekly by default."""

        period_part = self.get_period_part(period)
        url = '/%s/watched/%s' % (media_type, period_part)
        
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def collected(self, irc, msg, args, media_type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]
        Returns top 10 collected movies or shows. Weekly by default."""

        period_part = self.get_period_part(period)
        url = '/%s/collected/%s' % (media_type, period_part)
        
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows'))])
    def anticipated(self, irc, msg, args, media_type):
        """<movies|shows>
        Returns top 10 anticipated movies or shows."""

        url = '/%s/anticipated' % media_type
        
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movie', 'show')), 'text'])
    def rating(self, irc, msg, args, media_type, name):
        """<movies|show> <name>

        Returns rating with distribution of votes for movies or shows."""
        #values = " ▁▂▃▄▅▆▇█❘"
        title, slug = self.search_item_by_title_and_type(name, media_type)
        if (title is None or slug is None):
            irc.reply('Sorry, no hits.')
            return

        url = '/%s/%s/ratings' % (media_type + 's', slug)
        data = self.apicall(url)

        rating = data.get('rating')
        votes = data.get('votes')

        distribution = data.get('distribution')
        sortedlist = [(k, distribution[k]) for k in sorted(distribution, key=float)]
        sorted_scores = [num for score, num in sortedlist]

        biggest = max(sorted_scores)
        weightedDistribution = [score / biggest for score in sorted_scores]
        graph = self.create_graph_for_range(weightedDistribution)

        output = '%s rated %.1f by %s people: 0 %s10' % (title, rating, votes, graph)
        irc.reply(output)

    def create_graph_for_range(self, values):
        output = ''
        for r in values:
            output += self.get_graph_level(r)
        output += '❘'
        return output

    def get_graph_level(self, value):
        if (value <= 0.0): return " "
        if (value > 0.0 and value <= 0.1): return "▁"
        if (value > 0.1 and value <= 0.2): return "▂"
        if (value > 0.2 and value <= 0.3): return "▃"
        if (value > 0.3 and value <= 0.4): return "▄"
        if (value > 0.4 and value <= 0.5): return "▅"
        if (value > 0.5 and value <= 0.6): return "▆"
        if (value > 0.6 and value <= 0.7): return "▆"
        if (value > 0.7 and value <= 0.8): return "▇"
        if (value > 0.8 and value <= 0.9): return "█"
        if (value > 0.9): return "█"

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

    def search_item_by_title_and_type(self, search, search_type):
        url = '/search/%s?query=%s' % (search_type, urllib.parse.quote(search))
        data = self.apicall(url)

        if (len(data) == 0): return None, None
        show = data[0]
        title = show.get(search_type).get('title')
        slug = show.get(search_type).get('ids').get('slug')
        return title, slug

Class = TraktTV
