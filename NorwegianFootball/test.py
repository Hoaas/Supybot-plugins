###
# Copyright (c) 2023, Terje Hoås
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

from . import plugin as norwegianfootball_plugin


def makeResult(home90, away90, home120=None, away120=None,
               homePen=None, awayPen=None):
    """Build a NIFS result object."""
    r = {'homeScore90': home90, 'awayScore90': away90}
    if home120 is not None:
        r['homeScore120'] = home120
        r['awayScore120'] = away120
    if homePen is not None:
        r['homeScorePenalties'] = homePen
        r['awayScorePenalties'] = awayPen
    return r


def makeEvent(eventId, matchId, matchName, result, comment=None):
    """Build a single NIFS match event entry."""
    return {
        'id': eventId,
        'matchId': matchId,
        'comment': comment,
        'match': {
            'id': matchId,
            'name': matchName,
            'result': result,
        },
    }


def makeData(*events):
    """Serialise a list of events to JSON bytes."""
    return json.dumps(list(events)).encode()


# ---------------------------------------------------------------------------
# Unit tests for module-level helpers — no bot, no network
# ---------------------------------------------------------------------------

class FormatScoreTestCase(SupyTestCase):

    def testNormalMatch(self):
        result = makeResult(2, 1)
        self.assertEqual(norwegianfootball_plugin.formatScore(result), '2 - 1')

    def testAfterExtraTime(self):
        result = makeResult(1, 1, home120=2, away120=1)
        self.assertEqual(norwegianfootball_plugin.formatScore(result), '2 - 1 (aet)')

    def testAfterPenalties(self):
        result = makeResult(1, 1, home120=1, away120=1, homePen=4, awayPen=3)
        self.assertEqual(norwegianfootball_plugin.formatScore(result), '1 - 1 (4 - 3 pen)')

    def testZeroZero(self):
        result = makeResult(0, 0)
        self.assertEqual(norwegianfootball_plugin.formatScore(result), '0 - 0')


class FindMatchesTestCase(SupyTestCase):

    def testMatchWithComment(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0),
                      comment='Rosenborg scores!')
        )
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 0 - Rosenborg scores!'])

    def testMatchWithoutAnyComment(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0))
        )
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 0'])

    def testLatestCommentUsedNotLatestEvent(self):
        # Event 1: goal with comment; Event 2: substitution, no comment, newer id.
        # Score must come from event 2 (latest), comment from event 1.
        result10 = makeResult(1, 0)
        result11 = makeResult(1, 0)
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', result10,
                      comment='Mål for Rosenborg!'),
            makeEvent(2, 10, 'Rosenborg - Molde', result11),
        )
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 0 - Mål for Rosenborg!'])

    def testScoreFromLatestEvent(self):
        # Event 1: 0-0, no comment; Event 2: 1-0, no comment.
        # Score must be 1-0 (from event 2).
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(0, 0)),
            makeEvent(2, 10, 'Rosenborg - Molde', makeResult(1, 0)),
        )
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 0'])

    def testSearchIsCaseInsensitive(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0))
        )
        result = norwegianfootball_plugin.findMatches('rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 0'])

    def testPartialNameMatches(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0))
        )
        result = norwegianfootball_plugin.findMatches('Mold', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 0'])

    def testNoMatchReturnsEmptyList(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0))
        )
        result = norwegianfootball_plugin.findMatches('Brann', data)
        self.assertEqual(result, [])

    def testMultipleDistinctMatchesReturned(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0),
                      comment='Mål!'),
            makeEvent(2, 20, 'Brann - Rosenborg II', makeResult(2, 1)),
        )
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(len(result), 2)
        self.assertIn('Rosenborg - Molde 1 - 0 - Mål!', result)
        self.assertIn('Brann - Rosenborg II 2 - 1', result)

    def testExtraTimeScoreShown(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde',
                      makeResult(1, 1, home120=2, away120=1))
        )
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 2 - 1 (aet)'])

    def testPenaltyScoreShown(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde',
                      makeResult(1, 1, home120=1, away120=1,
                                 homePen=5, awayPen=4))
        )
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 1 (5 - 4 pen)'])

    def testEntryWithoutMatchKeyIsSkipped(self):
        data = json.dumps([{'id': 1, 'comment': 'orphan'}]).encode()
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, [])

    def testEntryWithNullMatchIsSkipped(self):
        data = json.dumps([{'id': 1, 'match': None, 'comment': None}]).encode()
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, [])

    def testAcceptsStringInput(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0))
        ).decode()
        self.assertIsInstance(data, str)
        result = norwegianfootball_plugin.findMatches('Rosenborg', data)
        self.assertEqual(result, ['Rosenborg - Molde 1 - 0'])


# ---------------------------------------------------------------------------
# Integration tests for the bot command — network call is mocked
# ---------------------------------------------------------------------------

class NorwegianFootballCommandTestCase(PluginTestCase):
    plugins = ('NorwegianFootball',)

    def testCommandReturnsMatchWithComment(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0),
                      comment='Rosenborg scores!')
        )
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse(
                'fotball Rosenborg',
                'Rosenborg - Molde 1 - 0 - Rosenborg scores!'
            )
        finally:
            utils.web.getUrl = original

    def testCommandReturnsMatchWithoutComment(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(2, 0))
        )
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse('fotball Rosenborg', 'Rosenborg - Molde 2 - 0')
        finally:
            utils.web.getUrl = original

    def testCommandReturnsNoMatchFound(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0))
        )
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse('fotball Brann', 'No match found')
        finally:
            utils.web.getUrl = original

    def testCommandReturnsMultipleMatchesPipeSeparated(self):
        data = makeData(
            makeEvent(1, 10, 'Rosenborg - Molde', makeResult(1, 0),
                      comment='Mål!'),
            makeEvent(2, 20, 'Brann - Rosenborg II', makeResult(2, 1)),
        )
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            msg = self.getMsg('fotball Rosenborg')
            reply = msg.args[1]
            self.assertIn('Rosenborg - Molde 1 - 0 - Mål!', reply)
            self.assertIn('Brann - Rosenborg II 2 - 1', reply)
            self.assertIn(' | ', reply)
        finally:
            utils.web.getUrl = original
