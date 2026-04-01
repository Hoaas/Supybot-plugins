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

import json
import urllib.parse

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    import supybot.i18n as _i18n
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _i18nInstance = PluginInternationalization('SSB')

    def _(s):
        import supybot.conf as _conf
        try:
            lang = _conf.supybot.plugins.SSB.language()
        except Exception:
            lang = ''
        lang = lang or _i18n.currentLocale
        if _i18nInstance.currentLocaleName != lang:
            _i18nInstance.loadLocale(lang)
        return _i18nInstance(s)

except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


_TYPE_LABELS = {
    'family':          lambda: _('last name'),
    'firstgiven':      lambda: _('first name (with middle name)'),
    'onlygiven':       lambda: _('first name (only)'),
    'middleandfamily': lambda: _('middle + last name'),
}

_GENDER_LABELS = {
    'M': lambda: _('M'),
    'F': lambda: _('F'),
}


def formatNameResults(data):
    """Parse the SSB nameSearch API response and return a formatted string.

    data may be JSON bytes or a string. Returns a pipe-separated string of
    groups, each in the form 'NAME: count type, count type', or None if no
    docs are found. Gender is shown in parentheses for given names only.
    """
    if isinstance(data, bytes):
        data = data.decode()
    parsed = json.loads(data)
    docs = parsed.get('response', {}).get('docs', [])
    if not docs:
        return None

    # Group docs by name, preserving first-appearance order.
    groups = {}
    for d in docs:
        name = d.get('name') or ''
        groups.setdefault(name, []).append(d)

    group_parts = []
    for name, entries in groups.items():
        entry_parts = []
        for d in entries:
            count = d.get('count')
            type_key = d.get('type', '')
            gender_key = d.get('gender', '')
            label = _TYPE_LABELS.get(type_key, lambda: type_key)()
            gender_label = _GENDER_LABELS.get(gender_key)
            if gender_label is not None:
                entry_parts.append(f'{count} {label} ({gender_label()})')
            else:
                entry_parts.append(f'{count} {label}')
        group_parts.append(f'{name}: {", ".join(entry_parts)}')

    return ' | '.join(group_parts)


class SSB(callbacks.Plugin):
    """Looks up Norwegian name statistics from Statistics Norway (ssb.no)."""
    threaded = True

    @wrap(['text'])
    @internationalizeDocstring
    def navn(self, irc, msg, args, name):
        """<navn>

        Returnerer statistikk om et norsk navn fra Statistisk sentralbyrå."""
        url = f'https://www.ssb.no/_/service/mimir/nameSearch?name={urllib.parse.quote(name)}'
        data = utils.web.getUrl(url)
        result = formatNameResults(data)
        if result:
            irc.reply(result)
        else:
            irc.reply(_('No results found for that name'))

Class = SSB
