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
from datetime import date
from unittest.mock import patch

import supybot.utils as utils
from supybot.test import *

from . import plugin as series_plugin


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def makeEpisode(season=1, number=3, name='Pilot', airdate='2024-01-15'):
    ep = {
        'season': season,
        'name': name,
        'airdate': airdate,
    }
    if number is not None:
        ep['number'] = number
    return ep


def makeShow(name='Test Show', status='Running', url='https://www.tvmaze.com/shows/1/test',
             previous=None, next_ep=None, premiered='2022-01-01'):
    embedded = {}
    if previous:
        embedded['previousepisode'] = previous
    if next_ep:
        embedded['nextepisode'] = next_ep
    return {
        'name': name,
        'status': status,
        'url': url,
        'premiered': premiered,
        '_embedded': embedded,
    }


# ---------------------------------------------------------------------------
# Unit tests — formatEpisode
# ---------------------------------------------------------------------------

class FormatEpisodeTestCase(SupyTestCase):

    def testRegularEpisode(self):
        ep = makeEpisode(season=2, number=5, name='The One', airdate='2024-03-10')
        self.assertEqual(
            series_plugin.formatEpisode(ep),
            'S02E05 · The One · (2024-03-10)'
        )

    def testSpecialNoNumber(self):
        ep = {'season': 1, 'number': None, 'name': 'Holiday Special', 'airdate': '2024-12-25'}
        self.assertEqual(
            series_plugin.formatEpisode(ep),
            'S01 special · Holiday Special · (2024-12-25)'
        )

    def testNoAirdate(self):
        ep = {'season': 1, 'number': 1, 'name': 'Pilot', 'airdate': ''}
        self.assertEqual(series_plugin.formatEpisode(ep), 'S01E01 · Pilot')

    def testNoName(self):
        ep = {'season': 3, 'number': 2, 'name': '', 'airdate': '2024-05-01'}
        self.assertEqual(series_plugin.formatEpisode(ep), 'S03E02 · (2024-05-01)')

    def testNoneReturnsEmpty(self):
        self.assertEqual(series_plugin.formatEpisode(None), '')

    def testMissingSeasonReturnsEmpty(self):
        ep = {'number': 1, 'name': 'Pilot', 'airdate': '2024-01-01'}
        self.assertEqual(series_plugin.formatEpisode(ep), '')

    def testPaddingApplied(self):
        ep = makeEpisode(season=10, number=1, name='Ep', airdate='2024-01-01')
        result = series_plugin.formatEpisode(ep)
        self.assertTrue(result.startswith('S10E01'))


# ---------------------------------------------------------------------------
# Unit tests — parseShow
# ---------------------------------------------------------------------------

class ParseShowTestCase(SupyTestCase):

    def testBasicFieldsExtracted(self):
        js = makeShow(name='Severance', status='Running')
        show = series_plugin.parseShow(js)
        self.assertIsNotNone(show)
        self.assertEqual(show['name'], 'Severance')
        self.assertEqual(show['status'], 'Running')

    def testPreviousEpisodeExtracted(self):
        prev = makeEpisode(season=2, number=10, name='Finale', airdate='2025-03-21')
        js = makeShow(previous=prev)
        show = series_plugin.parseShow(js)
        self.assertEqual(show['previous']['name'], 'Finale')
        self.assertIsNone(show['next'])

    def testNextEpisodeExtracted(self):
        nxt = makeEpisode(season=3, number=1, name='Premiere', airdate='2026-01-01')
        js = makeShow(next_ep=nxt)
        show = series_plugin.parseShow(js)
        self.assertEqual(show['next']['name'], 'Premiere')
        self.assertIsNone(show['previous'])

    def testBothEpisodesExtracted(self):
        prev = makeEpisode(season=1, number=5, name='Old', airdate='2023-01-01')
        nxt = makeEpisode(season=1, number=6, name='New', airdate='2023-02-01')
        js = makeShow(previous=prev, next_ep=nxt)
        show = series_plugin.parseShow(js)
        self.assertIsNotNone(show['previous'])
        self.assertIsNotNone(show['next'])

    def testNoEmbeddedKeyReturnsNoneEpisodes(self):
        js = {'name': 'Test', 'status': 'Ended', 'url': ''}
        show = series_plugin.parseShow(js)
        self.assertIsNone(show['previous'])
        self.assertIsNone(show['next'])

    def testMissingNameReturnsNone(self):
        self.assertIsNone(series_plugin.parseShow({'status': 'Running'}))

    def testNoneInputReturnsNone(self):
        self.assertIsNone(series_plugin.parseShow(None))

    def testNonDictInputReturnsNone(self):
        self.assertIsNone(series_plugin.parseShow('not a dict'))


# ---------------------------------------------------------------------------
# Unit tests — dateAge
# ---------------------------------------------------------------------------

class DateAgeTestCase(SupyTestCase):

    def _age(self, airdate, today_str):
        today = date.fromisoformat(today_str)
        with patch('Series.plugin.date') as mock_date:
            mock_date.today.return_value = today
            mock_date.fromisoformat = date.fromisoformat
            return series_plugin.dateAge(airdate)

    def testToday(self):
        self.assertEqual(self._age('2025-06-01', '2025-06-01'), 'today')

    def testOneDay(self):
        self.assertEqual(self._age('2025-05-31', '2025-06-01'), '1 day')

    def testSeveralDays(self):
        self.assertEqual(self._age('2025-05-25', '2025-06-01'), '7 days')

    def testOneMonth(self):
        self.assertEqual(self._age('2025-05-01', '2025-06-01'), '1 month')

    def testSeveralMonths(self):
        self.assertEqual(self._age('2025-01-01', '2025-06-01'), '5 months')

    def testOneYear(self):
        self.assertEqual(self._age('2024-06-01', '2025-06-01'), '1 year')

    def testSeveralYears(self):
        self.assertEqual(self._age('2021-06-01', '2025-06-01'), '4 years')

    def testFutureDate(self):
        self.assertEqual(self._age('2025-06-08', '2025-06-01'), '7 days')

    def testEmptyReturnsEmpty(self):
        self.assertEqual(series_plugin.dateAge(''), '')

    def testInvalidReturnsEmpty(self):
        self.assertEqual(series_plugin.dateAge('not-a-date'), '')


# ---------------------------------------------------------------------------
# Unit tests — formatEpisodeTv
# ---------------------------------------------------------------------------

class FormatEpisodeTvTestCase(SupyTestCase):

    def _fmt(self, ep, today_str='2026-01-01'):
        today = date.fromisoformat(today_str)
        with patch('Series.plugin.date') as mock_date:
            mock_date.today.return_value = today
            mock_date.fromisoformat = date.fromisoformat
            return series_plugin.formatEpisodeTv(ep)

    def testRegularEpisode(self):
        ep = makeEpisode(season=2, number=12, name='Jedha, Kyber, Erso', airdate='2025-05-13')
        result = self._fmt(ep)
        self.assertIn('[2x12]', result)
        self.assertIn('Jedha, Kyber, Erso', result)
        self.assertIn('on 2025-05-13', result)

    def testSpecialNoNumber(self):
        ep = {'season': 1, 'name': 'Holiday Special', 'airdate': '2024-12-25'}
        result = self._fmt(ep)
        self.assertIn('[1x special]', result)
        self.assertIn('Holiday Special', result)

    def testNoneReturnsEmpty(self):
        self.assertEqual(series_plugin.formatEpisodeTv(None), '')

    def testMissingSeasonReturnsEmpty(self):
        ep = {'number': 1, 'name': 'Pilot', 'airdate': '2024-01-01'}
        self.assertEqual(series_plugin.formatEpisodeTv(ep), '')

    def testAgeIncluded(self):
        ep = makeEpisode(season=2, number=12, name='Ep', airdate='2025-05-13')
        result = self._fmt(ep, today_str='2026-01-01')
        # ~7.5 months back — should show months
        self.assertRegex(result, r'\(\d+ months?\)')

    def testNoAirdate(self):
        ep = {'season': 1, 'number': 1, 'name': 'Pilot', 'airdate': ''}
        result = series_plugin.formatEpisodeTv(ep)
        self.assertIn('[1x01]', result)
        self.assertIn('Pilot', result)
        self.assertNotIn('on', result)


# ---------------------------------------------------------------------------
# Integration tests — bot command
# ---------------------------------------------------------------------------

class SeriesCommandTestCase(PluginTestCase):
    plugins = ('Series',)

    def testEpReturnsPrevAndNext(self):
        prev = makeEpisode(season=2, number=10, name='Cold Harbor', airdate='2025-03-21')
        nxt = makeEpisode(season=3, number=1, name='Premiere', airdate='2026-01-01')
        payload = json.dumps(makeShow(name='Severance', status='Running',
                                      previous=prev, next_ep=nxt)).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: payload
        try:
            self.assertRegexp('ep Severance', r'Severance.*Prev:.*S02E10.*Next:.*S03E01')
        finally:
            utils.web.getUrl = original

    def testEpEndedShowNoNext(self):
        prev = makeEpisode(season=5, number=16, name='Felina', airdate='2013-09-29')
        payload = json.dumps(makeShow(name='Breaking Bad', status='Ended',
                                      previous=prev)).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: payload
        try:
            self.assertRegexp('ep Breaking Bad', r'Breaking Bad.*Ended.*Prev:.*S05E16')
            self.assertNotRegexp('ep Breaking Bad', r'Next:')
        finally:
            utils.web.getUrl = original

    def testEpNoEpisodeInfo(self):
        payload = json.dumps(makeShow(name='Obscure Show', status='In Development')).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: payload
        try:
            self.assertRegexp('ep Obscure Show', r'No episode information available')
        finally:
            utils.web.getUrl = original

    def testEpNotFound(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: (_ for _ in ()).throw(
            utils.web.Error('404 Not Found')
        )
        try:
            self.assertResponse('ep xyzzy no such show', 'Show not found.')
        finally:
            utils.web.getUrl = original

    def testTvReturnsSummary(self):
        prev = makeEpisode(season=2, number=12, name='Jedha, Kyber, Erso', airdate='2025-05-13')
        payload = json.dumps(makeShow(
            name='Andor', status='Ended', premiered='2022-09-21',
            url='https://www.tvmaze.com/shows/52341/andor',
            previous=prev,
        )).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: payload
        try:
            self.assertRegexp(
                'tv Andor',
                r'Andor.*2022.*Ended.*Previous Episode:.*\[2x12\].*not yet scheduled'
            )
        finally:
            utils.web.getUrl = original

    def testTvWithNextEpisode(self):
        prev = makeEpisode(season=1, number=5, name='Old', airdate='2024-01-01')
        nxt = makeEpisode(season=1, number=6, name='New', airdate='2025-09-01')
        payload = json.dumps(makeShow(
            name='Running Show', status='Running', premiered='2024-01-01',
            url='https://www.tvmaze.com/shows/99/running',
            previous=prev, next_ep=nxt,
        )).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: payload
        try:
            self.assertRegexp(
                'tv Running Show',
                r'Running Show.*Next Episode:.*\[1x06\]'
            )
        finally:
            utils.web.getUrl = original

    def testTvNotFound(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: (_ for _ in ()).throw(
            utils.web.Error('404 Not Found')
        )
        try:
            self.assertResponse('tv xyzzy no such show', 'Show not found.')
        finally:
            utils.web.getUrl = original
