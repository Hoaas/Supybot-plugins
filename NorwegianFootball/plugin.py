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
from supybot.commands import *
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('NorwegianFootball')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


def formatScore(result):
    """Return a human-readable score string from a NIFS result object.

    Picks the highest available phase: penalties > 120 min > 90 min.
    """
    home90 = result.get('homeScore90')
    away90 = result.get('awayScore90')
    homePen = result.get('homeScorePenalties')
    awayPen = result.get('awayScorePenalties')
    home120 = result.get('homeScore120')
    away120 = result.get('awayScore120')

    if homePen is not None and awayPen is not None:
        return f'{home90} - {away90} ({homePen} - {awayPen} pen)'
    if home120 is not None and away120 is not None:
        return f'{home120} - {away120} (aet)'
    return f'{home90} - {away90}'


def findMatches(search, data):
    """Return a list of formatted result strings for NIFS match events.

    Searches the event feed for matches whose name contains search
    (case-insensitive). For each matched match:
      - uses the most recent event (highest id) for the current score
      - uses the most recent event with a non-null comment for commentary

    data may be bytes or str. Returns [] if no match is found.
    """
    if isinstance(data, bytes):
        data = data.decode()
    events = json.loads(data)

    # Group events by matchId, keeping only those for matching match names.
    byMatch = {}
    for event in events:
        match = event.get('match')
        if match is None:
            continue
        name = match.get('name')
        if name is None:
            continue
        if search.lower() not in name.lower():
            continue
        matchId = match.get('id')
        if matchId is None:
            continue
        if matchId not in byMatch:
            byMatch[matchId] = []
        byMatch[matchId].append(event)

    results = []
    for matchEvents in byMatch.values():
        # Most recent event by id gives the authoritative current result.
        latestEvent = max(matchEvents, key=lambda e: e.get('id', 0))
        match = latestEvent['match']
        name = match.get('name', '')
        result = match.get('result') or {}
        score = formatScore(result)

        # Most recent event that has a non-null comment.
        commented = [e for e in matchEvents if e.get('comment') is not None]
        if commented:
            latestComment = max(commented, key=lambda e: e.get('id', 0))
            line = f'{name} {score} - {latestComment["comment"]}'
        else:
            line = f'{name} {score}'

        results.append(line)

    return results


class NorwegianFootball(callbacks.Plugin):
    """Fetches live match events and scores from the NIFS football API.
    Data is sourced from Norway and match names and commentary are in Norwegian."""
    threaded = True

    @wrap(['text'])
    @internationalizeDocstring
    def fotball(self, irc, msg, args, search):
        """<team>

        Shows the latest score and commentary for a Norwegian football match
        from NIFS. Match names and commentary are in Norwegian."""
        url = 'https://v3api.nifs.no/matchEvents/?latest=1'
        data = utils.web.getUrl(url)
        results = findMatches(search, data)
        if results:
            irc.reply(' | '.join(results))
        else:
            irc.reply(_('No match found'))

Class = NorwegianFootball
