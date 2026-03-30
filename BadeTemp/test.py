###
# Copyright (c) 2017, Terje Hoås
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
from datetime import datetime, timedelta, timezone

import supybot.utils as utils
from supybot.test import *

from . import plugin as badetemp_plugin


def makeEntry(regionName, locationName, temp, daysAgo=1):
    """Build a single yr.no water temperature JSON entry."""
    t = datetime.now(timezone.utc) - timedelta(days=daysAgo)
    return {
        'location': {
            'name': locationName,
            'region': {'name': regionName},
        },
        'time': t.isoformat(),
        'temperature': temp,
    }


def makeData(*entries):
    """Serialise a list of entries to JSON bytes."""
    return json.dumps(list(entries)).encode()


# ---------------------------------------------------------------------------
# Unit tests for the fetchTemps helper — no bot, no network
# ---------------------------------------------------------------------------

class FetchTempsTestCase(SupyTestCase):

    def testMatchReturnsFormattedString(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8))
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, ['4.8° Sollerudstranda'])

    def testMatchIsCaseInsensitive(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8))
        result = badetemp_plugin.fetchTemps('oslo', data)
        self.assertEqual(result, ['4.8° Sollerudstranda'])

    def testPartialRegionNameMatches(self):
        data = makeData(makeEntry('Stor-Oslo', 'Tjuvholmen', 4.2))
        result = badetemp_plugin.fetchTemps('oslo', data)
        self.assertEqual(result, ['4.2° Tjuvholmen'])

    def testNoMatchReturnsEmptyList(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8))
        result = badetemp_plugin.fetchTemps('Bergen', data)
        self.assertEqual(result, [])

    def testMultipleMatchesReturnedInOrder(self):
        data = makeData(
            makeEntry('Oslo', 'Sollerudstranda', 4.8),
            makeEntry('Oslo', 'Tjuvholmen', 4.2),
        )
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, ['4.8° Sollerudstranda', '4.2° Tjuvholmen'])

    def testStaleEntryIsExcluded(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8, daysAgo=8))
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, [])

    def testRecentEntryOnBoundaryIsIncluded(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8, daysAgo=6))
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, ['4.8° Sollerudstranda'])

    def testMixedFreshAndStaleEntriesOnlyReturnsFresh(self):
        data = makeData(
            makeEntry('Oslo', 'Sollerudstranda', 4.8, daysAgo=1),
            makeEntry('Oslo', 'Tjuvholmen', 3.1, daysAgo=8),
        )
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, ['4.8° Sollerudstranda'])

    def testEntryWithoutRegionIsSkipped(self):
        entry = {
            'location': {'name': 'Nowhere'},
            'time': datetime.now(timezone.utc).isoformat(),
            'temperature': 5.0,
        }
        data = json.dumps([entry]).encode()
        result = badetemp_plugin.fetchTemps('Nowhere', data)
        self.assertEqual(result, [])

    def testEntryWithoutLocationIsSkipped(self):
        entry = {
            'time': datetime.now(timezone.utc).isoformat(),
            'temperature': 5.0,
        }
        data = json.dumps([entry]).encode()
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, [])

    def testAcceptsBytesInput(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8))
        self.assertIsInstance(data, bytes)
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, ['4.8° Sollerudstranda'])

    def testAcceptsStringInput(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8)).decode()
        self.assertIsInstance(data, str)
        result = badetemp_plugin.fetchTemps('Oslo', data)
        self.assertEqual(result, ['4.8° Sollerudstranda'])


# ---------------------------------------------------------------------------
# Integration tests for the bot command — network call is mocked
# ---------------------------------------------------------------------------

class BadeTempCommandTestCase(PluginTestCase):
    plugins = ('BadeTemp',)

    def testCommandReturnsMatch(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8))
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse('badetemp Oslo', '4.8° Sollerudstranda')
        finally:
            utils.web.getUrl = original

    def testCommandReturnsNotFoundMessage(self):
        data = makeData(makeEntry('Oslo', 'Sollerudstranda', 4.8))
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse(
                'badetemp Bergen',
                'No regions found with that name'
            )
        finally:
            utils.web.getUrl = original

    def testCommandReturnsMultipleResultsCommaSeparated(self):
        data = makeData(
            makeEntry('Oslo', 'Sollerudstranda', 4.8),
            makeEntry('Oslo', 'Tjuvholmen', 4.2),
        )
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse(
                'badetemp Oslo',
                '4.8° Sollerudstranda, 4.2° Tjuvholmen'
            )
        finally:
            utils.web.getUrl = original

