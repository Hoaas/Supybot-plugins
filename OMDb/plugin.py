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
import urllib.parse

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('OMDb')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


def metacolor(score):
    """Return score string coloured for Metacritic (green ≥60, yellow ≥40, red <40)."""
    if not score or not score.isdigit():
        return score or 'N/A'
    scoreNum = int(score)
    if scoreNum >= 60:
        return ircutils.mircColor(f'{score}%', 'Green')
    if scoreNum >= 40:
        return ircutils.mircColor(f'{score}%', 'Yellow')
    return ircutils.mircColor(f'{score}%', 'Red')


def imdbcolor(score):
    """Return score string coloured for IMDb (green ≥8, yellow ≥6, orange ≥4, red <4)."""
    try:
        scoreNum = float(score)
    except (ValueError, TypeError):
        return score or 'N/A'
    if scoreNum >= 8.0:
        return ircutils.mircColor(score, 'Green')
    if scoreNum >= 6.0:
        return ircutils.mircColor(score, 'Yellow')
    if scoreNum >= 4.0:
        return ircutils.mircColor(score, 'Orange')
    return ircutils.mircColor(score, 'Red')


def rtcolor(score):
    """Return score string coloured for Rotten Tomatoes (green ≥60 = Fresh, red <60 = Rotten)."""
    scoreStr = score.rstrip('%') if score else ''
    if not scoreStr.isdigit():
        return score or 'N/A'
    scoreNum = int(scoreStr)
    if scoreNum >= 60:
        return ircutils.mircColor(score, 'Green')
    return ircutils.mircColor(score, 'Red')


def getRating(ratings, source):
    """Return the Value for a given Source in the Ratings list, or None."""
    for entry in ratings:
        if entry.get('Source') == source:
            return entry.get('Value')
    return None


def formatResult(j):
    """Format an OMDb JSON result dict into an IRC reply string."""
    ratings = j.get('Ratings') or []
    metascore = getRating(ratings, 'Metacritic')
    if metascore:
        # Metacritic returns e.g. "74/100" — extract the numerator
        metascore = metascore.split('/')[0]
    rtScore = getRating(ratings, 'Rotten Tomatoes')
    imdbRating = j.get('imdbRating')

    parts = [
        ircutils.bold(j.get('Title', 'N/A')),
        f"({j.get('Year', 'N/A')})",
        j.get('Genre', 'N/A'),
        f"Metacritic: [{metacolor(metascore)}]",
        f"RT: [{rtcolor(rtScore)}]",
        f"IMDb: [{imdbcolor(imdbRating)}]",
        f"Actors: [{j.get('Actors', 'N/A')}]",
        j.get('Plot', 'N/A'),
    ]
    return ' '.join(parts)


class OMDb(callbacks.Plugin):
    """Looks up movie and series information from omdbapi.com, including Metacritic, Rotten Tomatoes, and IMDb ratings."""
    threaded = True

    @wrap([getopts({'year': 'int'}), 'text'])
    @internationalizeDocstring
    def omdb(self, irc, msg, args, opts, movie):
        """[--year <year>] <movie>

        Shows information about the given movie or series title, including
        Metacritic, Rotten Tomatoes, and IMDb ratings."""
        apikey = self.registryValue('apikey')
        if not apikey or apikey == 'Not set':
            irc.reply(_("API key not set. See 'config help supybot.plugins.OMDb.apikey'."))
            return

        params = {
            'apikey': apikey,
            't': movie,
            'plot': 'short',
            'r': 'json',
        }
        opts = dict(opts)
        year = opts.get('year')
        if year:
            params['y'] = year

        url = f'https://www.omdbapi.com/?{urllib.parse.urlencode(params)}'
        jsonstr = utils.web.getUrl(url).decode()
        j = json.loads(jsonstr)

        error = j.get('Error')
        if error:
            irc.reply(error)
            return

        irc.reply(formatResult(j))

Class = OMDb
