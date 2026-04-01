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
from datetime import date, datetime, timezone

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


def dateAge(airdate):
    """Return a human-readable age string for an ISO date string (YYYY-MM-DD).

    Examples: '3 days', '2 months', '1 year', '4 years'.
    Returns an empty string if airdate is empty or unparseable.
    """
    if not airdate:
        return ''
    try:
        aired = datetime.strptime(airdate, '%Y-%m-%d').date()
    except ValueError:
        return ''
    today = date.today()
    delta = abs((today - aired).days)
    if delta == 0:
        return 'today'
    if delta == 1:
        return '1 day'
    months = round(delta / 30.44)
    if months == 0:
        return f'{delta} days'
    if months < 12:
        plural = 's' if months > 1 else ''
        return f'{months} month{plural}'
    years = round(delta / 365.25)
    if years < 2:
        return '1 year'
    return f'{years} years'


def formatEpisodeTv(ep):
    """Format a TVmaze episode dict in the [SxEE] Name on date (age) style.

    Returns an empty string if ep is None or missing key fields.
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
        ep_code = f'[{season}x{number:02d}]'
    else:
        ep_code = f'[{season}x special]'

    parts = [ep_code]
    if name:
        parts.append(name)
    if airdate:
        age = dateAge(airdate)
        date_str = f'on {airdate}'
        if age:
            date_str += f' ({age})'
        parts.append(date_str)
    return ' '.join(parts)


def parseShow(js):
    """Parse a TVmaze singlesearch response (with embedded prev/next episodes).

    Returns a dict with keys:
        name        — show name string
        status      — show status string (e.g. 'Running', 'Ended')
        premiered   — premiered year string (e.g. '2022'), or empty string
        url         — TVmaze show URL string
        previous    — previous episode dict (or None)
        next        — next episode dict (or None)

    Returns None if js is None or missing the 'name' key.
    """
    if not isinstance(js, dict) or 'name' not in js:
        return None

    embedded = js.get('_embedded', {})
    premiered = js.get('premiered', '') or ''
    premiered_year = premiered[:4] if premiered else ''
    return {
        'name':      js.get('name', ''),
        'status':    js.get('status', ''),
        'premiered': premiered_year,
        'url':       js.get('url', ''),
        'previous':  embedded.get('previousepisode'),
        'next':      embedded.get('nextepisode'),
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

    @wrap(['text'])
    @internationalizeDocstring
    def tv(self, irc, msg, args, search):
        """<show name>

        Returns the status, premiered year, and previous/next episode of the
        given TV series, sourced from TVmaze."""
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

        name = ircutils.bold(show['name'])
        year = show['premiered']
        status = show['status']
        header = f'{name} {year} ({status}).' if year else f'{name} ({status}).'

        prev_str = formatEpisodeTv(show['previous'])
        next_str = formatEpisodeTv(show['next'])

        prev_part = f'Previous Episode: {prev_str}' if prev_str else _('Previous Episode: none.')
        next_part = f'Next Episode: {next_str}.' if next_str else _('Next Episode: not yet scheduled.')

        irc.reply(f'{header} {prev_part}. {next_part} {show["url"]}')


Class = Series
