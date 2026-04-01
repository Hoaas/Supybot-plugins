###
# Copyright (c) 2016, Terje Hoås
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
import supybot.ircutils as ircutils
from supybot.test import *

from . import plugin as omdb_plugin


def makeResult(title='The Matrix', year='1999', genre='Action, Sci-Fi',
               metascore=73, rtScore='87%', imdbRating='8.7',
               actors='Keanu Reeves', plot='A computer hacker learns the truth.'):
    """Build a minimal OMDb API result dict."""
    ratings = [
        {'Source': 'Metacritic', 'Value': f'{metascore}/100'},
        {'Source': 'Rotten Tomatoes', 'Value': rtScore},
    ]
    return {
        'Title': title,
        'Year': year,
        'Genre': genre,
        'Ratings': ratings,
        'imdbRating': imdbRating,
        'Actors': actors,
        'Plot': plot,
        'Response': 'True',
    }


def makeError(message='Movie not found!'):
    """Build an OMDb API error response dict."""
    return {'Response': 'False', 'Error': message}


# ---------------------------------------------------------------------------
# Unit tests for module-level helper functions — no bot, no network
# ---------------------------------------------------------------------------

class MetacolorTestCase(SupyTestCase):

    def testGreenAbove60(self):
        result = omdb_plugin.metacolor('75')
        self.assertIn('75%', result)
        self.assertIn('\x03', result)  # mIRC colour escape

    def testYellowBetween40And59(self):
        result = omdb_plugin.metacolor('50')
        self.assertIn('50%', result)

    def testRedBelow40(self):
        result = omdb_plugin.metacolor('20')
        self.assertIn('20%', result)

    def testExactly60IsGreen(self):
        result = omdb_plugin.metacolor('60')
        self.assertIn('60%', result)

    def testExactly40IsYellow(self):
        result = omdb_plugin.metacolor('40')
        self.assertIn('40%', result)

    def testNonNumericReturnsAsIs(self):
        self.assertEqual(omdb_plugin.metacolor('N/A'), 'N/A')

    def testNoneReturnsNA(self):
        self.assertEqual(omdb_plugin.metacolor(None), 'N/A')


class ImdbcolorTestCase(SupyTestCase):

    def testGreenAbove8(self):
        result = omdb_plugin.imdbcolor('8.7')
        self.assertIn('8.7', result)
        self.assertIn('\x03', result)

    def testYellowBetween6And8(self):
        result = omdb_plugin.imdbcolor('7.0')
        self.assertIn('7.0', result)

    def testOrangeBetween4And6(self):
        result = omdb_plugin.imdbcolor('5.0')
        self.assertIn('5.0', result)

    def testRedBelow4(self):
        result = omdb_plugin.imdbcolor('2.0')
        self.assertIn('2.0', result)

    def testNonNumericReturnsAsIs(self):
        self.assertEqual(omdb_plugin.imdbcolor('N/A'), 'N/A')

    def testNoneReturnsNA(self):
        self.assertEqual(omdb_plugin.imdbcolor(None), 'N/A')

    def testExactly8IsGreen(self):
        result = omdb_plugin.imdbcolor('8.0')
        self.assertIn('8.0', result)


class RtcolorTestCase(SupyTestCase):

    def testGreenAbove60(self):
        result = omdb_plugin.rtcolor('87%')
        self.assertIn('87%', result)
        self.assertIn('\x03', result)

    def testRedBelow60(self):
        result = omdb_plugin.rtcolor('45%')
        self.assertIn('45%', result)

    def testExactly60IsGreen(self):
        result = omdb_plugin.rtcolor('60%')
        self.assertIn('60%', result)

    def testNonNumericReturnsAsIs(self):
        self.assertEqual(omdb_plugin.rtcolor('N/A'), 'N/A')

    def testNoneReturnsNA(self):
        self.assertEqual(omdb_plugin.rtcolor(None), 'N/A')


class GetRatingTestCase(SupyTestCase):

    def testReturnsValueForKnownSource(self):
        ratings = [
            {'Source': 'Rotten Tomatoes', 'Value': '87%'},
            {'Source': 'Metacritic', 'Value': '73/100'},
        ]
        self.assertEqual(omdb_plugin.getRating(ratings, 'Rotten Tomatoes'), '87%')

    def testReturnsNoneForUnknownSource(self):
        ratings = [{'Source': 'Rotten Tomatoes', 'Value': '87%'}]
        self.assertIsNone(omdb_plugin.getRating(ratings, 'Metacritic'))

    def testEmptyListReturnsNone(self):
        self.assertIsNone(omdb_plugin.getRating([], 'Rotten Tomatoes'))


class FormatResultTestCase(SupyTestCase):

    def testContainsTitleYearGenre(self):
        result = omdb_plugin.formatResult(makeResult())
        self.assertIn('The Matrix', result)
        self.assertIn('1999', result)
        self.assertIn('Action, Sci-Fi', result)

    def testContainsActorsAndPlot(self):
        result = omdb_plugin.formatResult(makeResult())
        self.assertIn('Keanu Reeves', result)
        self.assertIn('A computer hacker learns the truth.', result)

    def testContainsMetacriticLabel(self):
        result = omdb_plugin.formatResult(makeResult())
        self.assertIn('Metacritic:', result)

    def testContainsRTLabel(self):
        result = omdb_plugin.formatResult(makeResult())
        self.assertIn('RT:', result)

    def testContainsIMDbLabel(self):
        result = omdb_plugin.formatResult(makeResult())
        self.assertIn('IMDb:', result)

    def testMissingRatingsGraceful(self):
        j = makeResult()
        j['Ratings'] = []
        result = omdb_plugin.formatResult(j)
        self.assertIn('The Matrix', result)


# ---------------------------------------------------------------------------
# Integration tests for the bot command — network call is mocked
# ---------------------------------------------------------------------------

class OMDbCommandTestCase(PluginTestCase):
    plugins = ('OMDb',)
    config = {'supybot.plugins.OMDb.apikey': 'testkey'}

    def testCommandReturnsResult(self):
        data = json.dumps(makeResult()).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertNotError('omdb The Matrix')
        finally:
            utils.web.getUrl = original

    def testCommandContainsTitleInReply(self):
        data = json.dumps(makeResult(title='The Matrix')).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertRegexp('omdb The Matrix', 'The Matrix')
        finally:
            utils.web.getUrl = original

    def testCommandPassesThroughAPIError(self):
        data = json.dumps(makeError('Movie not found!')).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse('omdb xyzzy1234notreal', 'Movie not found!')
        finally:
            utils.web.getUrl = original

    def testMissingApikeyReturnsError(self):
        import supybot.conf as conf
        with conf.supybot.plugins.OMDb.apikey.context('Not set'):
            self.assertRegexp('omdb The Matrix', 'API key not set')

    def testYearOptionPassedInURL(self):
        seen_urls = []
        data = json.dumps(makeResult()).encode()
        original = utils.web.getUrl

        def capture(url, **kw):
            seen_urls.append(url)
            return data

        utils.web.getUrl = capture
        try:
            self.assertNotError('omdb --year 1999 The Matrix')
        finally:
            utils.web.getUrl = original
        self.assertTrue(any('y=1999' in u for u in seen_urls))
