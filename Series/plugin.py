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
import urllib.parse

import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('Series')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f

API_BASE = 'https://api.tvmaze.com'


def formatEpisode(ep):
    """Format a TVmaze episode dict as 'S01E02 · Name (airdate)'.

    Returns an empty string if ep is None or missing key fields.
    Number may be None for specials; season is always present.
    """
    if not ep:
        return ''
    season = ep.get('season')
    number = ep.get('number')
    name = ep.get('name', '')
    airdate = ep.get('airdate', '')

    if season is None:
        return ''

    if number is not None:
        ep_code = f'S{season:02d}E{number:02d}'
    else:
        ep_code = f'S{season:02d} special'

    parts = [ep_code]
    if name:
        parts.append(name)
    if airdate:
        parts.append(f'({airdate})')
    return ' · '.join(parts) if len(parts) > 1 else ep_code


def parseShow(js):
    """Parse a TVmaze singlesearch response (with embedded prev/next episodes).

    Returns a dict with keys:
        name        — show name string
        status      — show status string (e.g. 'Running', 'Ended')
        url         — TVmaze show URL string
        previous    — previous episode dict (or None)
        next        — next episode dict (or None)

    Returns None if js is None or missing the 'name' key.
    """
    if not isinstance(js, dict) or 'name' not in js:
        return None

    embedded = js.get('_embedded', {})
    return {
        'name':     js.get('name', ''),
        'status':   js.get('status', ''),
        'url':      js.get('url', ''),
        'previous': embedded.get('previousepisode'),
        'next':     embedded.get('nextepisode'),
    }


class Series(callbacks.Plugin):
    """Returns TV show information and episode data via the TVmaze API."""
    threaded = True

    @wrap(['text'])
    @internationalizeDocstring
    def ep(self, irc, msg, args, search):
        """<show name>

        Returns the previous and next episode of the given TV series,
        sourced from TVmaze."""
        url = (
            f'{API_BASE}/singlesearch/shows'
            f'?q={urllib.parse.quote(search)}'
            f'&embed[]=previousepisode&embed[]=nextepisode'
        )
        try:
            data = utils.web.getUrl(url)
        except utils.web.Error:
            irc.reply(_('Show not found.'))
            return

        try:
            js = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            irc.reply(_('Failed to parse response from TVmaze.'))
            return

        show = parseShow(js)
        if show is None:
            irc.reply(_('Show not found.'))
            return

        header = ircutils.bold(show['name'])
        if show['status']:
            header += f' [{show["status"]}]'

        prev_str = formatEpisode(show['previous'])
        next_str = formatEpisode(show['next'])

        parts = [header]
        if prev_str:
            parts.append(f'Prev: {prev_str}')
        if next_str:
            parts.append(f'Next: {next_str}')
        if not prev_str and not next_str:
            parts.append(_('No episode information available.'))

        irc.reply(' | '.join(parts))


Class = Series
