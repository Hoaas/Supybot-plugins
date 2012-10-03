# coding=utf8
###
# Copyright (c) 2010, Terje Hoås
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
import os

#libraries for time_created_at
import time
from datetime import tzinfo, datetime, timedelta

import json
import urllib2, urllib

import supybot.dbi as dbi
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class LastFMNickRecord(dbi.Record):
    __fields__ = [
        ('nick', eval),
        ('username', eval),
        ]

class DbiLastFMNickDB(plugins.DbiChannelDB):
    class DB(dbi.DB):
        Record = LastFMNickRecord

        def add(self, nick, username):
            record = self.Record(nick=nick, username=username)
            super(self.__class__, self).add(record)

        def remove(self, nick):
            size = self.size()
            for i in range(1, size+1):
                u = self.get(i)
                if u.nick == nick:
                    self.remove(i)
                    return True
            return False

        def getusername(self, nick):
            size = self.size()
            for i in range(1, size+1):
                u = self.get(i)
                if u.nick == nick:  return u.username
            return nick

LASTFMNICKDB = plugins.DB('LastFM', {'flat': DbiLastFMNickDB})


apikey = 'Not set'
url ='http://ws.audioscrobbler.com/2.0/?'

class LastFM(callbacks.Plugin):
    """Simply returns current playing track for a LastFM user. If no track is
    currently playing the last played track will be displayed."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(LastFM, self)
        self.__parent.__init__(irc)
        self.db = LASTFMNICKDB()

    def add(self, irc, msg, args, username, nick):
        """<username> [nick]

        Links the callers nick to <username> on LastFM. If [nick] is given that is linked to <username> instead."""
        if not nick:
            nick = msg.nick
        channel = msg.args[0]

        oldname = self.db.getusername(channel, nick)
        if oldname != username:
            if self.db.remove(channel, nick):
                irc.reply('Naw, sorry. Changing username is temp. disabled.')
                return
                irc.reply('Updating LastFM nick for user %s from %s to %s.' % (nick, oldname, username))
        else:
            irc.reply('Storing LastFM nick %s for user %s.' % (username, nick))
        self.db.add(channel, nick, username)
    add = wrap(add, ['anything', optional('anything')])

    def whosplaying(self, irc, msg, args):
        """takes no arguments

        Currently playing track for all nicks in channel, if any."""
        self.set_apikey()
        channel = msg.args[0]
        playing = []
        for nick in irc.state.channels[msg.args[0]].users:
            nick = self.db.getusername(channel, nick)
            lp = self.last_played(nick, plays = False)
            if lp.find(' np. ') != -1:
                playing.append(lp)

        if len(playing) == 0:
            irc.reply('No users in the channel currently scrobbling.')
            return

        for status in playing:
            irc.reply(status)
    whosplaying = wrap(whosplaying)

    def set_apikey(self):
        self.apikey = self.registryValue('apikey')
        if not self.apikey or self.apikey == "Not set":
            irc.reply("API key not set. see 'config help supybot.plugins.LastFM.apikey'.")
            return


    def lastfm(self, irc, msg, args, user):
        """[user]

        Returns last played track for user. If no username is supplies, the
        nick of the one calling the command will be attempted."""
        
        if not user:
            user = msg.nick
        channel = msg.args[0]
        user = self.db.getusername(channel, user)

        reply = self.last_played(user)
        if reply:
            irc.reply(reply.encode('utf-8'))
    lastfm = wrap(lastfm, [optional('text')])

    def last_played(self, user, plays = True):
        self.set_apikey()
        data = urllib.urlencode(
            {'user': user,
            'limit' : 1,
            'api_key': self.apikey,
            'format': 'json',
            'method': 'user.getrecenttracks'}
        )

        try:
            text = utils.web.getUrl(url, data=data)
        except urllib2.HTTPError as err:
            if err.code == 403:
                return str(err) + ' API key not valid?'
            elif err.code == 400:
                return 'No such user.'
            else:
                return 'Could not open URL. ' + str(err)
        except urllib2.URLError as err:
            return 'Error accessing API. It might be down. Please try again later.'
        except urllib2.TIMED_OUT as err:
            return 'Connection timed out.'
        except:
            raise

        js = json.loads(text)

        try:
            js['error']
            return js['message']
        except: pass

        try:
            last_track = js['recenttracks']['track']
        except:
            return js['recenttracks']['user'] + ' has no recent tracks.'

        user = js['recenttracks']['@attr']['user']
        # Incase there is a list of tracks
        if type(last_track) == list: last_track = last_track[0]

        artist = last_track['artist']['#text']
        track = last_track['name']

        try:
            np = last_track['@attr']['nowplaying']
        except:
            np = False

        if not np:
            when = last_track['date']['#text']
            when = self._time_created_at(when) # Remove this line to output
                                               # date in UTC instead.
        if plays:
            plays = self.num_of_plays(last_track['mbid'], track, artist, user)
        if not plays:
            plays = ''

        if not artist or not track or not user:
            return
        if np:
            reply = "%s np. %s - %s%s" % (user, artist, track, plays)
        else:
            reply = "%s last played %s - %s%s (%s)" % (user, artist, track, plays, ircutils.bold(when))
        return reply

    def num_of_plays(self, mbid, track, artist, user):
        data = urllib.urlencode(
            {'mdib': mbid,
            'track': track.encode('utf8'),
            'artist': artist.encode('utf8'),
            'username': user,
            'autocorrect': 0,
            'api_key': self.apikey,
            'format': 'json',
            'method': 'track.getInfo'}
        )

        try:
            text = utils.web.getUrl(url, data=data)
        except:
            return

        js = json.loads(text)

        try:
            js['error']
            return
        except: pass

        try:
            play_count = js['track']['userplaycount']
        except:
            return
        loved = js['track']['userloved']

        plural = lambda n: 's' if int(n) > 1 else ''

        if loved == '0':
            return ' [%s play%s]' % (play_count, plural(play_count))
        elif loved == '1':
            return ' [%s play%s %s]' % (play_count, plural(play_count), ircutils.bold('<3'))
        else:
            # This is pretty much for debugging. Not quite sure if this can
            # ever happen or not. And I have no loved tracks D:
            return ' [%s play%s %s]' % (play_count, plural(play_count), ircutils.bold(loved))


    def _time_created_at(self, s):
        """
        recieving text element of 'created_at' in the response of LastFM API,
        returns relative time string from now.
        """

        plural = lambda n: n > 1 and "s" or ""

        # LastFM returns dates in this format: 12 Aug 2012, 17:09
        # and it is in GMT
        try:
            ddate = time.strptime(s, "%d %b %Y, %H:%M")[:-2]
        except ValueError:
            return "", ""

        created_at = datetime(*ddate, tzinfo=None)
        d = datetime.utcnow() - created_at

        if d.days:
            rel_time = "%s days ago" % d.days
        elif d.seconds > 3600:
            hours = d.seconds / 3600
            rel_time = "%s hour%s ago" % (hours, plural(hours))
        elif 60 <= d.seconds < 3600:
            minutes = d.seconds / 60
            rel_time = "%s minute%s ago" % (minutes, plural(minutes))
        elif 30 < d.seconds < 60:
            rel_time = "less than a minute ago"
        else:
            rel_time = "less than %s second%s ago" % (d.seconds, plural(d.seconds))
        return  rel_time

Class = LastFM


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
