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

import json
import time
import pickle
import random
import datetime
import urllib.parse
import urllib.error

import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('TraktTV')
except ImportError:
    _ = lambda x: x

filename = conf.supybot.directories.data.dirize('TraktTV.pickle')

api_url = 'https://api.trakt.tv'


class TraktTV(callbacks.Plugin):
    """Limnoria plugin for the Trakt.tv API.

    Supports now-playing lookups, trending/popular/played/watched/collected/
    anticipated lists, ratings, random episode picks, and OAuth device-flow
    authentication.
    """
    threaded = True

    def get_client_id(self):
        return self.registryValue('client_id')

    def get_client_secret(self):
        return self.registryValue('client_secret')

    def _convert_timestamp(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc)
        age = datetime.datetime.now(datetime.timezone.utc) - dt

        plural = lambda n: 's' if n > 1 else ''

        if age.days:
            return f'{int(age.days)} day{plural(age.days)} ago'
        elif age.seconds > 3600:
            hours = age.seconds / 3600
            return f'{int(hours)} hour{plural(hours)} ago'
        elif 60 <= age.seconds < 3600:
            minutes = age.seconds / 60
            return f'{int(minutes)} minute{plural(minutes)} ago'
        elif 30 < age.seconds < 60:
            return 'less than a minute ago'
        else:
            return f'less than {int(age.seconds)} second{plural(age.seconds)} ago'

    def get_access_token(self):
        auth = None
        try:
            with open(filename, 'rb') as pkl:
                auth = pickle.load(pkl)
                self.log.debug('Auth from pickle-file: %s', auth)
        except IOError as e:
            self.log.debug('Unable to open pickled file: %s', e)

        if not auth:
            self.log.debug('No pickle file with access_token. Not previously logged in')
            return None

        exp = auth.get('expires_in')
        created = auth.get('created_at')
        now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
        expires_at = created + exp

        self.log.debug('Auth token valid for %s days.', (expires_at - now) / (60 * 60 * 24))
        self.log.debug('Auth token created at %s', datetime.datetime.fromtimestamp(created, tz=datetime.timezone.utc))

        if expires_at - now < 60 * 60 * 24 * 60:
            # If less than 60 days of validity remain, renew
            # (it's valid for 90 days, so we renew on first use after a month)
            refresh_token = auth.get('refresh_token')
            auth = self.renew_access_token(refresh_token)

        return auth.get('access_token')

    def renew_access_token(self, refresh_token):
        self.log.debug('Renewing token.')

        values = {
            'refresh_token': refresh_token,
            'client_id': self.get_client_id(),
            'client_secret': self.get_client_secret(),
            'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
            'grant_type': 'refresh_token',
        }

        headers = {
            'Content-Type': 'application/json',
        }

        token_url = f'{api_url}/oauth/token'

        response = utils.web.getUrl(token_url, headers=headers, data=json.dumps(values))
        response = response.decode()

        self.log.debug('Renew token response: %s', response)

        auth = json.loads(response)

        with open(filename, 'wb') as pkl:
            pickle.dump(auth, pkl)
        return auth

    def auth(self, irc):
        self.log.debug('Creating new access token.')
        values = {
            'client_id': self.get_client_id(),
        }
        headers = {
            'Content-Type': 'application/json',
        }

        codes_url = f'{api_url}/oauth/device/code'

        self.log.debug('Accessing %s', codes_url)
        self.log.debug('%s', json.dumps(values))

        response = utils.web.getUrl(codes_url, headers=headers, data=json.dumps(values))
        response = response.decode()

        codes = json.loads(response)

        self.log.debug('Codes response: %s', codes)
        irc.reply(f'Visit {codes.get("verification_url")} and input {codes.get("user_code")}.')

        token_url = f'{api_url}/oauth/device/token'
        authed = False
        interval = codes.get('interval')
        time_max = codes.get('expires_in')
        time_expired = 0

        values = {
            'client_id': self.get_client_id(),
            'client_secret': self.get_client_secret(),
            'code': codes.get('device_code'),
        }

        auth = None
        while not authed and time_expired < time_max:
            time.sleep(interval)
            time_expired += interval
            time_max = 30
            self.log.info('Time expired: %s', time_expired)

            try:
                response = utils.web.getUrl(token_url, headers=headers, data=json.dumps(values))
            except utils.web.Error as err:
                err_str = str(err)
                if '400' in err_str:  # Pending - waiting for user to authorize your app
                    continue
                if '404' in err_str:  # Not Found - invalid device_code
                    irc.error('Not Found - invalid device_code. Report a bug at https://github.com/Hoaas/Supybot-plugins/issues/new?title=TraktTV:%20Invalid%20device_code')
                    return
                if '409' in err_str:  # Already Used - user already approved this code
                    irc.error('This code is already used. Try again?')
                    return
                if '410' in err_str:  # Expired - the tokens have expired, restart the process
                    irc.error('The tokens have expired. Try again?')
                    return
                if '418' in err_str:  # Denied - user explicitly denied this code
                    irc.error('You have to press the other button! (the green one that says YES)')
                    return
                if '429' in err_str:  # Slow Down - your app is polling too quickly
                    irc.error('Slow Down - your app is polling too quickly. Report a bug at https://github.com/Hoaas/Supybot-plugins/issues/new?title=TraktTV:%20429%20Slow%20Down')
                    return
                irc.error(err_str)
                return

            authed = True

            response = response.decode()

            self.log.debug('Response: %s', response)

            auth = json.loads(response)

        with open(filename, 'wb') as pkl:
            pickle.dump(auth, pkl)
        irc.reply('Authed!')

    @wrap([optional('text')])
    def np(self, irc, msg, args, nick):
        """[nick]

        Show currently playing movie/show from TraktTV. Needs to be a public
        profile. If no nick is supplied the IRC nick of the caller is attempted."""

        if not nick:
            nick = msg.nick

        url = f'{api_url}/users/{nick}/watching'
        headers = {
            'Content-type': 'application/json',
            'trakt-api-key': self.get_client_id(),
            'trakt-api-version': '2',
        }

        access_token = self.get_access_token()
        if access_token:
            headers['Authorization'] = f'Bearer {access_token}'

        try:
            self.log.debug('Trying %s with these headers: %s', url, headers)
            data = utils.web.getUrl(url, headers=headers).decode()
        except utils.web.Error as err:
            err_str = str(err)
            if '404' in err_str:
                irc.error(f'User {nick} not found on Trakt.TV.')
                return
            if '401' in err_str:
                self.auth(irc)
                return
            irc.error(err_str)
            return

        if not data:
            irc.reply('Not currently scrobbling.')
            return

        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            irc.error('Failed to parse response from trakt.tv.')
            raise

        if len(data) == 0:
            irc.error(f"Shouldn't really happen. Got an empty reply. But {nick} is probably not playing anything.")
            return

        show = data.get('show')
        if show:
            title = show.get('title')
            episode = data.get('episode')
            season = episode.get('season')
            ep_number = episode.get('number')
            ep_title = episode.get('title')
            output = f'{nick} np. {ircutils.bold(title)} - {ep_title} (s{season:02d}e{ep_number:02d})'
            irc.reply(output)
            return

        movie = data.get('movie')
        if movie:
            title = movie.get('title')
            year = movie.get('year')
            output = f'{nick} np. {ircutils.bold(title)} ({year})'
            irc.reply(output)
            return

        irc.error("Don't know what to do with this data. Not a show or a movie?")

    @wrap(['text'])
    def random(self, irc, msg, args, show):
        """<show>

        Returns a random episode for a given show."""

        title, slug = self.search_item_by_title_and_type(show, 'show')
        if title is None or slug is None:
            irc.reply('Sorry, no hits.')
            return

        url = f'/shows/{slug}/seasons?extended=episodes'

        data = self.apicall(url)

        random_season = random.choice(data).get('episodes')
        random_episode = random.choice(random_season)

        ep = random_episode

        output = f'Your random episode: {title} - {ep.get("title")} (s{ep.get("season"):02d}e{ep.get("number"):02d})'
        irc.reply(output)

    @wrap([('literal', ('movies', 'shows'))])
    def trending(self, irc, msg, args, media_type):
        """<movies|shows>

        Returns top 10 trending movies or shows."""

        url = f'/{media_type}/trending'
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows'))])
    def popular(self, irc, msg, args, media_type):
        """<movies|shows>

        Returns top 10 popular movies or shows."""

        url = f'/{media_type}/popular'
        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def played(self, irc, msg, args, media_type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]

        Returns top 10 played movies or shows. Weekly by default."""

        period_part = self.get_period_part(period)
        url = f'/{media_type}/played/{period_part}'

        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def watched(self, irc, msg, args, media_type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]

        Returns top 10 watched movies or shows. Weekly by default."""

        period_part = self.get_period_part(period)
        url = f'/{media_type}/watched/{period_part}'

        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows')), optional(('literal', ('daily', 'weekly', 'monthly', 'yearly')))])
    def collected(self, irc, msg, args, media_type, period):
        """<movies|shows> [daily|weekly|monthly|yearly]

        Returns top 10 collected movies or shows. Weekly by default."""

        period_part = self.get_period_part(period)
        url = f'/{media_type}/collected/{period_part}'

        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movies', 'shows'))])
    def anticipated(self, irc, msg, args, media_type):
        """<movies|shows>

        Returns top 10 anticipated movies or shows."""

        url = f'/{media_type}/anticipated'

        irc.reply(self.get_lists(url))

    @wrap([('literal', ('movie', 'show')), 'text'])
    def rating(self, irc, msg, args, media_type, name):
        """<movie|show> <name>

        Returns rating with distribution of votes for movies or shows."""

        title, slug = self.search_item_by_title_and_type(name, media_type)
        if title is None or slug is None:
            irc.reply('Sorry, no hits.')
            return

        url = f'/{media_type}s/{slug}/ratings'
        data = self.apicall(url)

        rating = data.get('rating')
        votes = data.get('votes')

        distribution = data.get('distribution')
        sortedlist = [(k, distribution[k]) for k in sorted(distribution, key=float)]
        sorted_scores = [num for score, num in sortedlist]

        biggest = max(sorted_scores)
        weightedDistribution = [score / biggest for score in sorted_scores]
        graph = self.create_graph_for_range(weightedDistribution)

        output = f'{title} rated {rating:.1f} by {votes} people: 0 {graph}10'
        irc.reply(output)

    def create_graph_for_range(self, values):
        output = ''
        for r in values:
            output += self.get_graph_level(r)
        output += '❘'
        return output

    def get_graph_level(self, value):
        if value <= 0.0: return ' '
        if value <= 0.1: return '▁'
        if value <= 0.2: return '▂'
        if value <= 0.3: return '▃'
        if value <= 0.4: return '▄'
        if value <= 0.5: return '▅'
        if value <= 0.6: return '▆'
        if value <= 0.7: return '▆'
        if value <= 0.8: return '▇'
        if value <= 0.9: return '█'
        return '█'

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
            'trakt-api-version': '2',
        }

        if client_id:
            headers['trakt-api-key'] = self.get_client_id()

        if auth_token:
            access_token = self.get_access_token()
            if access_token:
                headers['Authorization'] = f'Bearer {access_token}'
            else:
                self.log.error('TraktTV: Failed to get access token.')
                return

        url = f'{api_url}{url}'

        data = utils.web.getUrl(url, headers=headers).decode()
        data = json.loads(data)
        return data

    def search_item_by_title_and_type(self, search, search_type):
        url = f'/search/{search_type}?query={urllib.parse.quote(search)}'
        data = self.apicall(url)

        if len(data) == 0:
            return None, None
        show = data[0]
        title = show.get(search_type).get('title')
        slug = show.get(search_type).get('ids').get('slug')
        return title, slug


Class = TraktTV
