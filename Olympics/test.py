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
from supybot.test import *

from . import plugin as olympicsplugin

# Fixture data used across both test classes
SAMPLE_COUNTRY_NOR = {
    'description': 'Norway',
    'rank': 1,
    'medalsNumber': [
        {'type': 'Total', 'gold': 5, 'silver': 3, 'bronze': 2, 'total': 10},
        {'type': 'Alpine Skiing', 'gold': 2, 'silver': 1, 'bronze': 0, 'total': 3},
    ],
}

SAMPLE_COUNTRY_GER = {
    'description': 'Germany',
    'rank': 2,
    'medalsNumber': [
        {'type': 'Total', 'gold': 3, 'silver': 4, 'bronze': 1, 'total': 8},
    ],
}

SAMPLE_COUNTRY_NO_TOTAL = {
    'description': 'Freedonia',
    'rank': 3,
    'medalsNumber': [
        {'type': 'Alpine Skiing', 'gold': 1, 'silver': 0, 'bronze': 0, 'total': 1},
    ],
}

SAMPLE_API_RESPONSE = {
    'medalStandings': {
        'medalsTable': [
            SAMPLE_COUNTRY_NOR,
            SAMPLE_COUNTRY_GER,
        ],
    },
}


class OlympicsHelperTestCase(SupyTestCase):
    """Unit tests for the module-level helper functions."""

    def testGetTotalMedalsNormal(self):
        gold, silver, bronze = olympicsplugin.getTotalMedals(SAMPLE_COUNTRY_NOR)
        self.assertEqual(gold, 5)
        self.assertEqual(silver, 3)
        self.assertEqual(bronze, 2)

    def testGetTotalMedalsMissingTotal(self):
        """Countries without a Total entry return zeros."""
        gold, silver, bronze = olympicsplugin.getTotalMedals(SAMPLE_COUNTRY_NO_TOTAL)
        self.assertEqual((gold, silver, bronze), (0, 0, 0))

    def testGetTotalMedalsEmptyCountry(self):
        gold, silver, bronze = olympicsplugin.getTotalMedals({})
        self.assertEqual((gold, silver, bronze), (0, 0, 0))

    def testGetMedalCountsSingleKey(self):
        result = olympicsplugin.getMedalCounts(SAMPLE_COUNTRY_NOR, 'gold')
        self.assertEqual(result, (5,))

    def testGetMedalCountsMultipleKeys(self):
        result = olympicsplugin.getMedalCounts(SAMPLE_COUNTRY_NOR, 'gold', 'silver', 'bronze')
        self.assertEqual(result, (5, 3, 2))

    def testGetMedalCountsMissingKey(self):
        result = olympicsplugin.getMedalCounts(SAMPLE_COUNTRY_NOR, 'platinum')
        self.assertEqual(result, (0,))

    def testGetMedalCountsMissingTotal(self):
        result = olympicsplugin.getMedalCounts(SAMPLE_COUNTRY_NO_TOTAL, 'gold', 'silver')
        self.assertEqual(result, (0, 0))

    def testCreateReplyFormat(self):
        reply = olympicsplugin.createReply(SAMPLE_COUNTRY_NOR, 1)
        self.assertIn('Norway', reply)
        self.assertIn('1.', reply)
        self.assertIn('5', reply)   # gold count
        self.assertIn('3', reply)   # silver count
        self.assertIn('2', reply)   # bronze count
        self.assertIn('Total: 10', reply)

    def testCreateReplyPlace(self):
        reply = olympicsplugin.createReply(SAMPLE_COUNTRY_GER, 2)
        self.assertTrue(reply.startswith('2.'))

    def testCreateReplyMissingDescription(self):
        country = {'medalsNumber': [{'type': 'Total', 'gold': 1, 'silver': 0, 'bronze': 0, 'total': 1}]}
        reply = olympicsplugin.createReply(country, 1)
        self.assertIn('Unknown', reply)

    def testCreateReplyNoTotalEntry(self):
        """Countries with no Total entry should show zeros."""
        reply = olympicsplugin.createReply(SAMPLE_COUNTRY_NO_TOTAL, 3)
        self.assertIn('Freedonia', reply)
        self.assertIn('Total: 0', reply)


class OlympicsCommandTestCase(PluginTestCase):
    """Integration tests for the medals command."""
    plugins = ('Olympics',)

    def testMedalsCommand(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: json.dumps(SAMPLE_API_RESPONSE).encode()
        try:
            self.assertNotError('medals')
        finally:
            utils.web.getUrl = original

    def testMedalsReplyContainsTopCountry(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: json.dumps(SAMPLE_API_RESPONSE).encode()
        try:
            self.assertRegexp('medals', r'Norway')
        finally:
            utils.web.getUrl = original

    def testMedalsReplyContainsGoldCount(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: json.dumps(SAMPLE_API_RESPONSE).encode()
        try:
            self.assertRegexp('medals', r'5')
        finally:
            utils.web.getUrl = original

    def testMedalsEmptyStandings(self):
        """An API response with no countries should not raise an error."""
        original = utils.web.getUrl
        empty = {'medalStandings': {'medalsTable': []}}
        utils.web.getUrl = lambda url, **kw: json.dumps(empty).encode()
        try:
            # No replies expected, but also no error
            self.feedMsg('medals')
        finally:
            utils.web.getUrl = original

    def testMedalsHelp(self):
        self.assertHelp('help medals')
