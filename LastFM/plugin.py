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
import json
import time
import urllib.parse
from datetime import datetime, timezone

from supybot import dbi, utils, plugins, ircutils, callbacks
from supybot.commands import *

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('LastFM')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f

API_URL = 'https://ws.audioscrobbler.com/2.0/?'


def timeSince(s):
    """Convert a LastFM date string (e.g. '12 Aug 2012, 17:09' UTC) to a
    human-readable relative time string.  Returns an empty string on failure.
    """
    try:
        ddate = time.strptime(s, '%d %b %Y, %H:%M')[:-2]
    except ValueError:
        return ''

    created_at = datetime(*ddate, tzinfo=timezone.utc)
    d = datetime.now(timezone.utc) - created_at

    plural = lambda n: 's' if n > 1 else ''

    if d.days:
        return f'{d.days} day{plural(d.days)} ago'
    if d.seconds > 3600:
        hours = d.seconds // 3600
        return f'{hours} hour{plural(hours)} ago'
    if d.seconds >= 60:
        minutes = d.seconds // 60
        return f'{minutes} minute{plural(minutes)} ago'
    if d.seconds > 30:
        return 'less than a minute ago'
    return f'less than {d.seconds} second{plural(d.seconds)} ago'


def parseRecentTracks(text):
    """Parse a user.getRecentTracks JSON response.

    Returns a dict with keys:
        error   — error message string if the API returned an error, else None
        user    — LastFM username string
        np      — True if currently playing, False otherwise
        artist  — artist name string
        track   — track name string
        album   — album name string
        mbid    — track MusicBrainz ID string (may be empty)
        when    — raw LastFM date string if not now-playing, else None

    Returns None if the JSON cannot be parsed or is missing expected fields.
    """
    try:
        js = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None

    if 'error' in js:
        return {'error': js.get('message', 'Unknown error')}

    try:
        recenttracks = js['recenttracks']
        last_track = recenttracks['track']
        user = recenttracks['@attr']['user']
    except (KeyError, TypeError):
        return None

    if isinstance(last_track, list):
        if not last_track:
            return {'error': f'{user} has no recent tracks.'}
        last_track = last_track[0]

    try:
        artist = last_track['artist']['#text']
        track = last_track['name']
        album = last_track['album']['#text']
        mbid = last_track.get('mbid', '')
    except (KeyError, TypeError):
        return None

    if not artist or not track or not user:
        return None

    try:
        np = last_track['@attr']['nowplaying']
    except KeyError:
        np = False

    when = None
    if not np:
        try:
            when = last_track['date']['#text']
        except (KeyError, TypeError):
            when = None

    return {
        'error':  None,
        'user':   user,
        'np':     np,
        'artist': artist,
        'track':  track,
        'album':  album,
        'mbid':   mbid,
        'when':   when,
    }


def parsePlayInfo(js):
    """Parse a track.getInfo JSON response and return a formatted extras string.

    The string includes play count, loved status, and duration.  Returns an
    empty string if the response contains an error or missing fields.
    """
    if not isinstance(js, dict) or 'error' in js:
        return ''

    track = js.get('track')
    if not track:
        return ''

    play_count = track.get('userplaycount')
    loved = track.get('userloved')
    duration = track.get('duration')

    plural = lambda n: 's' if int(n) > 1 else ''
    heart = lambda h: ircutils.bold(' <3') if h == '1' else ''

    minutes = seconds = None
    if duration:
        total_secs = int(duration) // 1000
        minutes = total_secs // 60
        seconds = total_secs % 60

    retvalue = ''
    if play_count or loved == '1':
        retvalue += ' ['
        if play_count:
            retvalue += f'{play_count} play{plural(play_count)}'
        if loved:
            retvalue += heart(loved)
        retvalue += ']'
    if minutes is not None:
        retvalue += f' [{minutes}:{seconds:02d}]'
    return retvalue


def parseTopTags(js, maxtags=4):
    """Parse an artist.getTopTags JSON response and return a comma-separated
    tag string, or an empty string on error.
    """
    if not isinstance(js, dict) or 'error' in js:
        return ''

    toptags = js.get('toptags', {})
    if not toptags:
        return ''
    tags_data = toptags.get('tag')
    if not tags_data:
        return ''

    if isinstance(tags_data, dict):
        return tags_data.get('name', '')

    names = []
    for tag in tags_data[:maxtags]:
        name = tag.get('name')
        if name:
            names.append(name)
    return ', '.join(names)


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
            for i in range(1, size + 1):
                u = self.get(i)
                if u.nick == nick:
                    super(self.__class__, self).remove(i)
                    return True
            return False

        def getusername(self, nick):
            size = self.size()
            for i in range(1, size + 1):
                u = self.get(i)
                if u.nick == nick:
                    return u.username, True
            return nick, False


LASTFMNICKDB = plugins.DB('LastFM', {'flat': DbiLastFMNickDB})


class LastFM(callbacks.Plugin):
    """Returns the current or last played track for a LastFM user."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(LastFM, self)
        self.__parent.__init__(irc)
        self.db = LASTFMNICKDB()

    def _apikey(self):
        key = self.registryValue('apikey')
        if not key or key == 'Not set':
            raise callbacks.Error(
                _("API key not set. See 'config help supybot.plugins.LastFM.apikey'.")
            )
        return key

    @wrap(['anything', optional('anything')])
    @internationalizeDocstring
    def add(self, irc, msg, args, username, nick):
        """<username> [nick]

        Links the caller's nick to <username> on LastFM. If [nick] is given,
        that nick is linked instead."""
        if not nick:
            nick = msg.nick
        channel = msg.args[0]

        oldname, username_in_db = self.db.getusername(channel, nick)
        if username_in_db and oldname != username:
            self.db.remove(channel, nick)

        self.db.add(channel, nick, username)
        irc.reply(_('Storing LastFM nick %s for user %s.') % (username, nick))

    @wrap([getopts({'allatonce': '', 'skipplays': ''})])
    @internationalizeDocstring
    def whosplaying(self, irc, msg, args, opts):
        """[--allatonce] [--skipplays]

        Shows the currently playing track for all nicks in the channel."""
        apikey = self._apikey()
        channel = msg.args[0]

        allatonce = False
        skipplays = False
        for key, value in opts:
            if key == 'allatonce':
                allatonce = True
            if key == 'skipplays':
                skipplays = True

        playing = []
        users = list(irc.state.channels[channel].users)

        for nick in users:
            username, username_in_db = self.db.getusername(channel, nick)
            if not username_in_db:
                continue
            lp = self._lastPlayed(username, apikey, fetchPlays=not skipplays)
            if lp and ' np. ' in lp:
                playing.append(lp)
                if not allatonce:
                    irc.reply(lp)

        if not playing:
            irc.reply(_('No users in the channel currently scrobbling.'))
            return
        if allatonce:
            for output in playing:
                irc.reply(output)

    @wrap([getopts({'notags': ''}), optional('text')])
    @internationalizeDocstring
    def lastfm(self, irc, msg, args, options, user):
        """[--notags] [user]

        Returns the last played track for user. If no username is given, the
        nick of the caller is used."""
        if not user:
            user = msg.nick
        channel = msg.args[0]
        user, _in_db = self.db.getusername(channel, user)

        fetchplays = True
        if options:
            for key, _value in options:
                if key == 'notags':
                    fetchplays = False

        apikey = self._apikey()
        reply = self._lastPlayed(user, apikey, fetchPlays=fetchplays)
        if reply:
            irc.reply(reply)

    def _lastPlayed(self, user, apikey, fetchPlays=True):
        """Fetch and format the last/now-playing track for a LastFM user."""
        params = urllib.parse.urlencode({
            'user': user,
            'limit': 1,
            'api_key': apikey,
            'format': 'json',
            'method': 'user.getRecentTracks',
        })
        text = utils.web.getUrl(API_URL, data=params.encode()).decode()

        data = parseRecentTracks(text)
        if data is None:
            self.log.warning('LastFM: failed to parse recenttracks response for %s', user)
            return None
        if data.get('error'):
            return data['error']

        now_or_last = 'np.' if data['np'] else 'last played'

        when = ''
        if not data['np'] and data['when']:
            rel = timeSince(data['when'])
            if rel:
                when = f' ({ircutils.bold(rel)})'

        plays = ''
        if fetchPlays:
            plays = self._fetchPlayInfo(
                data['mbid'], data['artist'], data['track'],
                data['album'], data['user'], apikey,
            )

        return f'{data["user"]} {now_or_last} {data["artist"]} - {data["track"]}{plays}{when}'

    def _fetchPlayInfo(self, mbid, artist, track, album, user, apikey):
        """Fetch play count, loved status and duration from track.getInfo."""
        params = urllib.parse.urlencode({
            'mbid': mbid,
            'track': track,
            'artist': artist,
            'username': user,
            'autocorrect': 0,
            'api_key': apikey,
            'format': 'json',
            'method': 'track.getInfo',
        })
        try:
            text = utils.web.getUrl(API_URL, data=params.encode()).decode()
            js = json.loads(text)
        except (utils.web.Error, json.JSONDecodeError):
            self.log.info('LastFM: failed to fetch track.getInfo for %s - %s', artist, track)
            return ''

        play_info = parsePlayInfo(js)

        # Append genre tags from artist.getTopTags
        mbid_artist = ''
        try:
            mbid_artist = js['track']['artist']['mbid']
        except (KeyError, TypeError):
            pass
        tags = self._fetchTags(artist, mbid_artist, apikey)
        if tags:
            play_info += f' [{tags}]'

        return play_info

    def _fetchTags(self, artist, mbid, apikey):
        """Fetch top tags for an artist and return a comma-separated string."""
        if not artist and not mbid:
            return ''
        params = urllib.parse.urlencode({
            'artist': artist,
            'mbid': mbid or '',
            'api_key': apikey,
            'format': 'json',
            'method': 'artist.getTopTags',
        })
        try:
            text = utils.web.getUrl(API_URL, data=params.encode()).decode()
            js = json.loads(text)
        except (utils.web.Error, json.JSONDecodeError):
            self.log.info('LastFM: failed to fetch artist.getTopTags for %s', artist)
            return ''
        return parseTopTags(js)


Class = LastFM
