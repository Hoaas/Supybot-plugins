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
#from xml.etree import ElementTree
import urllib.request, urllib.error, urllib.parse, urllib.request, urllib.parse, urllib.error

import supybot.dbi as dbi
import supybot.utils as utils
#from supybot.commands import *
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
                if u.nick == nick:
                    return u.username, True
            return nick, False

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

        oldname, username_in_db = self.db.getusername(channel, nick)
        if oldname != username:
            if self.db.remove(channel, nick):
                #irc.reply('Naw, sorry. Changing username is temp. disabled.')
                return
                #irc.reply('Updating LastFM nick for user %s from %s to %s.' % (nick, oldname, username))
        irc.reply('Storing LastFM nick %s for user %s.' % (username, nick))
        self.db.add(channel, nick, username)
    add = wrap(add, ['anything', optional('anything')])

    def whosplaying(self, irc, msg, args, opts):
        """[--allatonce] [--skipplays]

        Currently playing track for all nicks in channel, if any."""
        self.set_apikey()
        channel = msg.args[0]

        atonce = True
        play_now = True
        for key, value in opts:
            if key == 'allatonce':
                atonce = False
            if key == 'skipplays':
                play_now = False

        playing = []
        # Copy the current users in the channel to avoid
        # RuntimeError: Set changed size during iteration
        users = []
        for u in irc.state.channels[msg.args[0]].users:
            users.append(u)

        for nick in users:
            nick, username_in_db = self.db.getusername(channel, nick)
            if not username_in_db:
                continue
            lp = self.last_played(nick, plays = play_now)
            if lp.find(' np. ') != -1: # if np. exists in string
                playing.append(lp)
                if atonce:
                    irc.reply(lp)

        if len(playing) == 0:
            irc.reply('No users in the channel currently scrobbling.')
            return
        if not atonce:
            for output in playing:
                irc.reply(output)
    whosplaying = wrap(whosplaying, [getopts({'allatonce':'', 'skipplays':''})])

    def set_apikey(self):
        self.apikey = self.registryValue('apikey')
        if not self.apikey or self.apikey == "Not set":
            raise Exception('Apikey not set. Check out config help supybot.plugins.LastFM.apikey')

    def lastfm(self, irc, msg, args, options, user):
        """[--notags][user]

        Returns last played track for user. If no username is supplies, the
        nick of the one calling the command will be attempted."""
        
        if not user:
            user = msg.nick
        channel = msg.args[0]
        user, username_in_db = self.db.getusername(channel, user)

        notags = True
        if options:
            for (key, value) in options:
                if key == 'notags':
                   notags = False

        reply = self.last_played(user, plays=notags)
        if reply:
            irc.reply(reply)
    lastfm = wrap(lastfm, [getopts({'notags':''}), optional('text')])

    def last_played(self, user, plays = True):
        self.set_apikey()
        data = urllib.parse.urlencode(
            {'user': user,
            'limit' : 1,
            'api_key': self.apikey,
            'format': 'json',
            'method': 'user.getRecentTracks'}
        ).encode('utf-8')
        text = utils.web.getUrl(url, data=data)
        text = text.decode()

        other, user, np, artist, track, plays, when = self._parseJson(text, plays)
        if other:
            if other == -1:
                return
            return other
        now = lambda n: 'np.' if n else 'last played'
        time_since = lambda w: ' (%s)' % ircutils.bold(w) if w else ''
        reply = '%s %s %s - %s%s%s' % (user, now(np), artist, track, plays, time_since(when))
        return reply

    #def _parseXml(self, text):
    #    tree = ElementTree.fromstring(text)
    #    recenttracks = tree.find('.//recenttracks')
    #    last_track = recenttracks.find('.//track')
    #    artist = last_track.find('.//artist').text
    #    album = last_track.find('.//album').text
    #    track = last_track.find('.//name').text

    #    user = recenttracks.attrib['user']
    #    #user = attr.find('.//user')
    #    return None, user, False, artist, track, "", None

    # Unknown if this works. Not tested.
    def _parseJson(self, text, plays): # Ok, wrongly named. This method actually does another call if plays is True
        js = json.loads(text)
        try:
            js['error']
            return js['message'], None, None, None, None, None, None
        except: pass

        try:
            last_track = js['recenttracks']['track'] # Might always happen after the API update
        except:
            return js['recenttracks']['user'] + ' has no recent tracks.', None, None, None, None, None, None

        user = js['recenttracks']['@attr']['user']
        # Incase there is a list of tracks
        if type(last_track) == list:
            if len(last_track) == 0:
                return user + ' has no recent tracks.', None, None, None, None, None, None
            last_track = last_track[0]

        artist = last_track['artist']['#text']
        album = last_track['album']['#text']
        track = last_track['name']

        try:
            np = last_track['@attr']['nowplaying']
        except:
            np = False

        when = False
        if not np:
            when = last_track['date']['#text']
            when = self._time_created_at(when) # Remove this line to output
                                               # date in UTC instead.
        if plays:
            plays = self.num_of_plays(last_track['mbid'], artist, track, album, user)
        if not plays:
            plays = ''

        if not artist or not track or not user:
            return -1
        return None, user, np, artist, track, plays, when


    def get_tags(self, artist, mbid):
        # Need either mbid or both artist and album.
        if mbid == '' and artist == '':
            return
        if mbid is None:
            mbid = ''
        data = urllib.parse.urlencode(
            {'artist': artist,
            'mbid': mbid,
            'api_key': self.apikey,
            'format': 'json',
            'method': 'artist.getTopTags'
            }
        )

        try:
            text = utils.web.getUrl(url, data=data).decode()
        except:
            return
        js = json.loads(text)
        tags = []
        toptags = js.get('toptags', '')
        if not toptags:
            self.log.info('Failed on url: ' + url + data)
            return
        toptags = toptags.get('tag')
        if not toptags:
            self.log.info('Failed on url: ' + url + data)
            return

        maxtags = 4
        i = 0

        if type(toptags) == dict:
            tags = toptags.get('name')
            return tags

        for tag in toptags:
            tags.append(tag.get('name'))
            i = i + 1
            if i >= maxtags:
                break
        tags = ', '.join(tags)
        return tags

    def num_of_plays(self, mbid_track, artist, track, album, user):
        data = urllib.parse.urlencode(
            {'mbid': mbid_track,
            'track': track,
            'artist': artist,
            'username': user,
            'autocorrect': 0,
            'api_key': self.apikey,
            'format': 'json',
            'method': 'track.getInfo'}
        ).encode('utf-8')
        try:
            text = utils.web.getUrl(url, data=data).decode()
        except:
            self.log.info('LastFM failed to access API in num_of_plays.')
            return

        js = json.loads(text)
        try:
            js['error']
            return
        except: pass

        track = js.get('track')
        if not track:
            return
        play_count = track.get('userplaycount')
        loved = track.get('userloved')
        duration = track.get('duration')
        if duration:
            duration = int(duration) / 1000
            minutes = int(duration / 60)
            seconds = int(duration % 60)

        plural = lambda n: 's' if int(n) > 1 else ''

        # If l is 1, reply <3.
        heart = lambda h: ircutils.bold(' <3') if h == '1' else ''
        tags = lambda t: ' [%s]' % t if t else ''

        mbid_artist = track.get('artist').get('mbid')
        t = self.get_tags(artist, mbid_artist)

        retvalue = ''

        # Things to output:
        # Play count, loved, tags and duration
        if play_count or loved == '1':
            retvalue += ' ['
            if play_count:
                retvalue += '%s play%s' % (play_count, plural(play_count))
            if loved:
                retvalue += '%s' % heart(loved)
            retvalue += ']'
        if t:
            retvalue += tags(t)
        if duration:
            retvalue += ' [%d:%02d]' % (minutes, seconds)
        if retvalue != '':
            return retvalue


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
            rel_time = "%s hour%s ago" % (int(hours), plural(hours))
        elif 60 <= d.seconds < 3600:
            minutes = d.seconds / 60
            rel_time = "%s minute%s ago" % (int(minutes), plural(minutes))
        elif 30 < d.seconds < 60:
            rel_time = "less than a minute ago"
        else:
            rel_time = "less than %s second%s ago" % (int(d.seconds), plural(d.seconds))
        return  rel_time

Class = LastFM
