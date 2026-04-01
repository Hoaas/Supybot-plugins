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

import io
import json
import pickle
import datetime
import unittest.mock

import supybot.utils as utils

from supybot.test import *

from . import plugin as trakttv_plugin


class TraktTVHelperTestCase(SupyTestCase):
    """Tests for pure helper functions that do not require a running bot."""

    def setUp(self):
        super().setUp()
        # Instantiate a bare object to access instance methods without full bot init
        self.plugin = trakttv_plugin.TraktTV.__new__(trakttv_plugin.TraktTV)

    def test_convert_timestamp_days(self):
        ts = (datetime.datetime.now() - datetime.timedelta(days=3)).timestamp()
        result = self.plugin._convert_timestamp(ts)
        self.assertEqual(result, '3 days ago')

    def test_convert_timestamp_hours(self):
        ts = (datetime.datetime.now() - datetime.timedelta(hours=5)).timestamp()
        result = self.plugin._convert_timestamp(ts)
        self.assertEqual(result, '5 hours ago')

    def test_convert_timestamp_minutes(self):
        ts = (datetime.datetime.now() - datetime.timedelta(minutes=10)).timestamp()
        result = self.plugin._convert_timestamp(ts)
        self.assertEqual(result, '10 minutes ago')

    def test_convert_timestamp_less_than_minute(self):
        ts = (datetime.datetime.now() - datetime.timedelta(seconds=45)).timestamp()
        result = self.plugin._convert_timestamp(ts)
        self.assertEqual(result, 'less than a minute ago')

    def test_convert_timestamp_seconds(self):
        ts = (datetime.datetime.now() - datetime.timedelta(seconds=10)).timestamp()
        result = self.plugin._convert_timestamp(ts)
        self.assertIn('second', result)

    def test_get_period_part_default(self):
        self.assertEqual(self.plugin.get_period_part(None), 'weekly')
        self.assertEqual(self.plugin.get_period_part('weekly'), 'weekly')

    def test_get_period_part_daily(self):
        self.assertEqual(self.plugin.get_period_part('daily'), 'daily')

    def test_get_period_part_monthly(self):
        self.assertEqual(self.plugin.get_period_part('monthly'), 'monthly')

    def test_get_period_part_yearly(self):
        self.assertEqual(self.plugin.get_period_part('yearly'), 'yearly')

    def test_get_graph_level(self):
        self.assertEqual(self.plugin.get_graph_level(0.0), ' ')
        self.assertEqual(self.plugin.get_graph_level(0.05), '▁')
        self.assertEqual(self.plugin.get_graph_level(0.95), '█')

    def test_create_graph_for_range(self):
        result = self.plugin.create_graph_for_range([0.0, 0.5, 1.0])
        self.assertTrue(result.endswith('❘'))
        self.assertEqual(len(result), 4)  # 3 chars + ❘


# Fake API responses for command tests
_TRENDING_MOVIES = json.dumps([
    {'watchers': 10, 'movie': {'title': 'Movie One', 'year': 2023, 'ids': {'slug': 'movie-one'}}},
    {'watchers': 9,  'movie': {'title': 'Movie Two', 'year': 2022, 'ids': {'slug': 'movie-two'}}},
])

_TRENDING_SHOWS = json.dumps([
    {'watchers': 5, 'show': {'title': 'Show One', 'year': 2021, 'ids': {'slug': 'show-one'}}},
    {'watchers': 4, 'show': {'title': 'Show Two', 'year': 2020, 'ids': {'slug': 'show-two'}}},
])

_POPULAR_MOVIES = json.dumps([
    {'title': 'Popular One', 'year': 2023, 'ids': {'slug': 'popular-one'}},
    {'title': 'Popular Two', 'year': 2022, 'ids': {'slug': 'popular-two'}},
])


class TraktTVCommandTestCase(PluginTestCase):
    """Tests for bot commands, with utils.web.getUrl monkey-patched."""

    plugins = ('TraktTV',)
    config = {
        'supybot.plugins.TraktTV.client_id': 'test_client_id',
        'supybot.plugins.TraktTV.client_secret': 'test_client_secret',
    }

    def _patch_getUrl(self, response_bytes):
        """Replace utils.web.getUrl with a stub returning response_bytes."""
        self._original_getUrl = utils.web.getUrl
        utils.web.getUrl = lambda url, **kwargs: response_bytes

    def _unpatch_getUrl(self):
        utils.web.getUrl = self._original_getUrl

    def testTrendingMovies(self):
        self._patch_getUrl(_TRENDING_MOVIES.encode())
        try:
            self.assertRegexp('trending movies', 'Movie One')
            self.assertRegexp('trending movies', 'Movie Two')
        finally:
            self._unpatch_getUrl()

    def testTrendingShows(self):
        self._patch_getUrl(_TRENDING_SHOWS.encode())
        try:
            self.assertRegexp('trending shows', 'Show One')
            self.assertRegexp('trending shows', 'Show Two')
        finally:
            self._unpatch_getUrl()

    def testPopularMovies(self):
        self._patch_getUrl(_POPULAR_MOVIES.encode())
        try:
            self.assertRegexp('popular movies', 'Popular One')
        finally:
            self._unpatch_getUrl()

    def testTrendingInvalidType(self):
        # 'trending' requires literal 'movies' or 'shows' — anything else is an error
        self.assertError('trending anime')

    def testPlayedDefaultPeriod(self):
        self._patch_getUrl(_TRENDING_MOVIES.encode())
        try:
            self.assertNotError('played movies')
        finally:
            self._unpatch_getUrl()

    def testWatchedWithPeriod(self):
        self._patch_getUrl(_TRENDING_MOVIES.encode())
        try:
            self.assertNotError('watched movies daily')
        finally:
            self._unpatch_getUrl()

    def testCollected(self):
        self._patch_getUrl(_TRENDING_MOVIES.encode())
        try:
            self.assertNotError('collected movies')
        finally:
            self._unpatch_getUrl()

    def testAnticipated(self):
        self._patch_getUrl(_TRENDING_MOVIES.encode())
        try:
            self.assertNotError('anticipated movies')
        finally:
            self._unpatch_getUrl()

    # NOTE: The `np` command requires OAuth token files on disk and a live
    # Trakt.tv user lookup. It is not tested here.
    # See PLAN.md for details on enabling that test with fixtures.


def _make_auth_pickle():
    """Return a BytesIO containing a valid-looking auth pickle."""
    now = int(datetime.datetime.now(datetime.timezone.utc).timestamp())
    auth = {
        'access_token': 'fake_access_token',
        'refresh_token': 'fake_refresh_token',
        'expires_in': 7776000,        # 90 days in seconds
        'created_at': now - 1000,     # created ~17 minutes ago — well within validity
    }
    buf = io.BytesIO(pickle.dumps(auth))
    return buf


_NP_SHOW_RESPONSE = json.dumps({
    'type': 'episode',
    'show': {'title': 'Breaking Bad', 'ids': {'slug': 'breaking-bad'}},
    'episode': {'season': 3, 'number': 7, 'title': 'One Minute'},
}).encode()

_NP_MOVIE_RESPONSE = json.dumps({
    'type': 'movie',
    'movie': {'title': 'The Matrix', 'year': 1999, 'ids': {'slug': 'the-matrix'}},
}).encode()

_NP_NOT_WATCHING_RESPONSE = b''


class TraktTVNpTestCase(PluginTestCase):
    """Tests for the np command, with open() and utils.web.getUrl mocked."""

    plugins = ('TraktTV',)
    config = {
        'supybot.plugins.TraktTV.client_id': 'test_client_id',
        'supybot.plugins.TraktTV.client_secret': 'test_client_secret',
    }

    def _patch(self, response_bytes):
        """Patch open() to return a valid auth pickle and getUrl to return response_bytes."""
        buf = _make_auth_pickle()
        mock_open = unittest.mock.mock_open(read_data=b'')
        mock_open.return_value.__enter__ = lambda s: buf
        mock_open.return_value.__exit__ = unittest.mock.Mock(return_value=False)
        self._open_patcher = unittest.mock.patch('builtins.open', mock_open)
        self._open_patcher.start()
        self._original_getUrl = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: response_bytes

    def _unpatch(self):
        self._open_patcher.stop()
        utils.web.getUrl = self._original_getUrl

    def testNpShow(self):
        self._patch(_NP_SHOW_RESPONSE)
        try:
            self.assertRegexp('np TestUser', r'Breaking Bad.*s03e07')
        finally:
            self._unpatch()

    def testNpMovie(self):
        self._patch(_NP_MOVIE_RESPONSE)
        try:
            self.assertRegexp('np TestUser', r'The Matrix.*1999')
        finally:
            self._unpatch()

    def testNpNotWatching(self):
        self._patch(_NP_NOT_WATCHING_RESPONSE)
        try:
            self.assertResponse('np TestUser', 'Not currently scrobbling.')
        finally:
            self._unpatch()
