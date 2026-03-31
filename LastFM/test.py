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

import supybot.utils as utils
from supybot.test import *

from . import plugin as lastfm_plugin


# ---------------------------------------------------------------------------
# JSON fixture builders
# ---------------------------------------------------------------------------

def makeTrack(artist='Radiohead', track='Creep', album='Pablo Honey',
              mbid='abc123', nowplaying=False, date='01 Jan 2024, 12:00'):
    t = {
        'artist': {'#text': artist, 'mbid': ''},
        'name': track,
        'album': {'#text': album},
        'mbid': mbid,
    }
    if nowplaying:
        t['@attr'] = {'nowplaying': 'true'}
    else:
        t['date'] = {'#text': date, 'uts': '1704110400'}
    return t


def makeRecentTracks(user='testuser', tracks=None, as_list=True):
    """Build a user.getRecentTracks JSON response."""
    if tracks is None:
        tracks = [makeTrack()]
    payload = tracks if as_list else tracks[0]
    return json.dumps({
        'recenttracks': {
            '@attr': {'user': user, 'page': '1', 'total': '100'},
            'track': payload,
        }
    })


def makeTrackInfo(artist='Radiohead', mbid='', userplaycount='5',
                  userloved='0', duration='238000'):
    """Build a track.getInfo JSON response."""
    return json.dumps({
        'track': {
            'name': 'Creep',
            'artist': {'name': artist, 'mbid': mbid},
            'userplaycount': userplaycount,
            'userloved': userloved,
            'duration': duration,
        }
    })


def makeTopTags(tags=None):
    """Build an artist.getTopTags JSON response."""
    if tags is None:
        tags = ['alternative rock', 'rock', 'radiohead']
    tag_list = [{'name': t, 'count': '100'} for t in tags]
    return json.dumps({'toptags': {'tag': tag_list}})


# ---------------------------------------------------------------------------
# Unit tests — timeSince
# ---------------------------------------------------------------------------

class TimeSinceTestCase(SupyTestCase):

    def testDaysAgo(self):
        # Build a date string 3 days in the past
        from datetime import datetime, timedelta, timezone
        dt = datetime.now(timezone.utc) - timedelta(days=3)
        s = dt.strftime('%d %b %Y, %H:%M')
        result = lastfm_plugin.timeSince(s)
        self.assertIn('3 day', result)
        self.assertIn('ago', result)

    def testHoursAgo(self):
        from datetime import datetime, timedelta, timezone
        dt = datetime.now(timezone.utc) - timedelta(hours=2)
        s = dt.strftime('%d %b %Y, %H:%M')
        result = lastfm_plugin.timeSince(s)
        self.assertIn('hour', result)
        self.assertIn('ago', result)

    def testMinutesAgo(self):
        from datetime import datetime, timedelta, timezone
        dt = datetime.now(timezone.utc) - timedelta(minutes=15)
        s = dt.strftime('%d %b %Y, %H:%M')
        result = lastfm_plugin.timeSince(s)
        self.assertIn('minute', result)
        self.assertIn('ago', result)

    def testLessThanMinute(self):
        from datetime import datetime, timedelta, timezone
        dt = datetime.now(timezone.utc) - timedelta(seconds=40)
        s = dt.strftime('%d %b %Y, %H:%M')
        result = lastfm_plugin.timeSince(s)
        self.assertIn('less than a minute ago', result)

    def testPluralDays(self):
        from datetime import datetime, timedelta, timezone
        dt = datetime.now(timezone.utc) - timedelta(days=5)
        s = dt.strftime('%d %b %Y, %H:%M')
        result = lastfm_plugin.timeSince(s)
        self.assertIn('days', result)

    def testSingularDay(self):
        from datetime import datetime, timedelta, timezone
        dt = datetime.now(timezone.utc) - timedelta(days=1, hours=1)
        s = dt.strftime('%d %b %Y, %H:%M')
        result = lastfm_plugin.timeSince(s)
        self.assertIn('1 day', result)
        self.assertNotIn('days', result)

    def testInvalidDateReturnsEmpty(self):
        result = lastfm_plugin.timeSince('not a date')
        self.assertEqual(result, '')


# ---------------------------------------------------------------------------
# Unit tests — parseRecentTracks
# ---------------------------------------------------------------------------

class ParseRecentTracksTestCase(SupyTestCase):

    def testNowPlayingParsed(self):
        text = makeRecentTracks(tracks=[makeTrack(nowplaying=True)])
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertIsNotNone(data)
        self.assertIsNone(data['error'])
        self.assertEqual(data['artist'], 'Radiohead')
        self.assertEqual(data['track'], 'Creep')
        self.assertEqual(data['user'], 'testuser')
        self.assertTrue(data['np'])
        self.assertIsNone(data['when'])

    def testLastPlayedParsed(self):
        text = makeRecentTracks(tracks=[makeTrack(date='01 Jan 2024, 12:00')])
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertIsNotNone(data)
        self.assertFalse(data['np'])
        self.assertEqual(data['when'], '01 Jan 2024, 12:00')

    def testApiErrorReturnsErrorDict(self):
        text = json.dumps({'error': 6, 'message': 'User not found'})
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['error'], 'User not found')

    def testEmptyTrackListReturnsError(self):
        text = makeRecentTracks(user='nobody', tracks=[], as_list=True)
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertIsNotNone(data)
        self.assertIn('nobody', data['error'])

    def testSingleTrackObjectParsed(self):
        # API can return a single dict instead of a list for one track
        text = makeRecentTracks(tracks=[makeTrack()], as_list=False)
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertIsNotNone(data)
        self.assertEqual(data['artist'], 'Radiohead')

    def testListWithMultipleTracksTakesFirst(self):
        tracks = [
            makeTrack(track='Creep', nowplaying=True),
            makeTrack(track='Karma Police', date='01 Jan 2024, 11:00'),
        ]
        text = makeRecentTracks(tracks=tracks)
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertEqual(data['track'], 'Creep')

    def testMbidExtracted(self):
        text = makeRecentTracks(tracks=[makeTrack(mbid='mbid-xyz')])
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertEqual(data['mbid'], 'mbid-xyz')

    def testAlbumExtracted(self):
        text = makeRecentTracks(tracks=[makeTrack(album='OK Computer')])
        data = lastfm_plugin.parseRecentTracks(text)
        self.assertEqual(data['album'], 'OK Computer')

    def testInvalidJsonReturnsNone(self):
        data = lastfm_plugin.parseRecentTracks('not json at all')
        self.assertIsNone(data)

    def testMissingRecentTracksKeyReturnsNone(self):
        data = lastfm_plugin.parseRecentTracks(json.dumps({'foo': 'bar'}))
        self.assertIsNone(data)


# ---------------------------------------------------------------------------
# Unit tests — parsePlayInfo
# ---------------------------------------------------------------------------

class ParsePlayInfoTestCase(SupyTestCase):

    def testPlayCountFormatted(self):
        js = json.loads(makeTrackInfo(userplaycount='7', userloved='0', duration='0'))
        result = lastfm_plugin.parsePlayInfo(js)
        self.assertIn('7 plays', result)

    def testSingularPlay(self):
        js = json.loads(makeTrackInfo(userplaycount='1', userloved='0', duration='0'))
        result = lastfm_plugin.parsePlayInfo(js)
        self.assertIn('1 play', result)
        self.assertNotIn('1 plays', result)

    def testDurationFormatted(self):
        js = json.loads(makeTrackInfo(duration='238000'))  # 3:58
        result = lastfm_plugin.parsePlayInfo(js)
        self.assertIn('[3:58]', result)

    def testLovedIncludesHeart(self):
        js = json.loads(makeTrackInfo(userloved='1', userplaycount='0', duration='0'))
        result = lastfm_plugin.parsePlayInfo(js)
        self.assertIn('<3', result)

    def testNeitherPlayCountNorLovedProducesNoBracket(self):
        js = json.loads(makeTrackInfo(userplaycount='0', userloved='0', duration='0'))
        result = lastfm_plugin.parsePlayInfo(js)
        # No play count bracket, but could still have duration if non-zero
        self.assertNotIn('plays', result)

    def testErrorResponseReturnsEmpty(self):
        js = {'error': 6, 'message': 'Track not found'}
        result = lastfm_plugin.parsePlayInfo(js)
        self.assertEqual(result, '')

    def testMissingTrackKeyReturnsEmpty(self):
        result = lastfm_plugin.parsePlayInfo({'foo': 'bar'})
        self.assertEqual(result, '')


# ---------------------------------------------------------------------------
# Unit tests — parseTopTags
# ---------------------------------------------------------------------------

class ParseTopTagsTestCase(SupyTestCase):

    def testTagsCommaSeparated(self):
        js = json.loads(makeTopTags(['rock', 'alternative', 'indie']))
        result = lastfm_plugin.parseTopTags(js)
        self.assertEqual(result, 'rock, alternative, indie')

    def testMaxFourTags(self):
        js = json.loads(makeTopTags(['a', 'b', 'c', 'd', 'e', 'f']))
        result = lastfm_plugin.parseTopTags(js)
        self.assertEqual(result, 'a, b, c, d')

    def testSingleTagAsDict(self):
        # API returns a dict instead of list when there is only one tag
        js = {'toptags': {'tag': {'name': 'rock', 'count': '100'}}}
        result = lastfm_plugin.parseTopTags(js)
        self.assertEqual(result, 'rock')

    def testErrorResponseReturnsEmpty(self):
        js = {'error': 6, 'message': 'Artist not found'}
        result = lastfm_plugin.parseTopTags(js)
        self.assertEqual(result, '')

    def testEmptyTagsReturnsEmpty(self):
        js = {'toptags': {'tag': []}}
        result = lastfm_plugin.parseTopTags(js)
        self.assertEqual(result, '')

    def testMissingToptagsReturnsEmpty(self):
        result = lastfm_plugin.parseTopTags({})
        self.assertEqual(result, '')


# ---------------------------------------------------------------------------
# Integration tests — bot commands with mocked network
# ---------------------------------------------------------------------------

class LastFMCommandTestCase(PluginTestCase):
    plugins = ('LastFM',)
    config = {'supybot.plugins.LastFM.apikey': 'testkey'}

    def testLastfmReturnsNowPlaying(self):
        recent = makeRecentTracks(
            user='testuser',
            tracks=[makeTrack(artist='Radiohead', track='Creep', nowplaying=True)],
        ).encode()
        track_info = makeTrackInfo(userplaycount='5', userloved='0', duration='0').encode()
        tags = makeTopTags(['rock']).encode()

        call_count = [0]
        def fakeGetUrl(url, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return recent
            if call_count[0] == 2:
                return track_info
            return tags

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            self.assertRegexp('lastfm testuser', r'testuser np\. Radiohead - Creep')
        finally:
            utils.web.getUrl = original

    def testLastfmReturnsLastPlayed(self):
        recent = makeRecentTracks(
            user='testuser',
            tracks=[makeTrack(artist='Radiohead', track='Karma Police',
                              date='01 Jan 2020, 12:00')],
        ).encode()
        track_info = makeTrackInfo(userplaycount='3', userloved='0', duration='0').encode()
        tags = makeTopTags([]).encode()

        call_count = [0]
        def fakeGetUrl(url, **kw):
            call_count[0] += 1
            if call_count[0] == 1:
                return recent
            if call_count[0] == 2:
                return track_info
            return tags

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            self.assertRegexp('lastfm testuser', r'testuser last played Radiohead - Karma Police')
        finally:
            utils.web.getUrl = original

    def testLastfmApiError(self):
        error_response = json.dumps({'error': 6, 'message': 'User not found'}).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: error_response
        try:
            self.assertResponse('lastfm nosuchuser', 'User not found')
        finally:
            utils.web.getUrl = original

    def testNoApikeyGivesError(self):
        with conf.supybot.plugins.LastFM.apikey.context('Not set'):
            self.assertError('lastfm testuser')
