###
# Copyright (c) 2015, Terje Hoås
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
import random
import time
from html.parser import HTMLParser

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('Kommune')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f

WIKIPEDIA_API_URL = (
    'https://no.wikipedia.org/w/api.php'
    '?action=parse&page=Norges_kommuner&prop=text'
    '&section=3&format=json&disablelimitreport=1'
)

CACHE_TTL = 86400  # 24 hours in seconds

# Column indices in the rendered table
_COL_NR = 0
_COL_NAVN = 1
_COL_ADM = 2
_COL_FYLKE = 3
_COL_FOLKETALL = 4
_COL_AREAL = 5
_COL_MALFORM = 8  # columns 6 (Kart) and 7 (Våpen) are images


class _TableParser(HTMLParser):
    """Extract rows from the first wikitable in an HTML fragment."""

    def __init__(self):
        super().__init__()
        self._in_table = False
        self._in_cell = False
        self._depth = 0          # nested table depth
        self._current_row = []
        self._current_cell = []
        self._sort_value = None  # data-sort-value on current <span>
        self.rows = []

    def handle_starttag(self, tag, attrs):
        attrdict = dict(attrs)
        if tag == 'table':
            if not self._in_table:
                classes = attrdict.get('class', '')
                if 'wikitable' in classes:
                    self._in_table = True
                    self._depth = 1
            else:
                self._depth += 1
            return
        if not self._in_table or self._depth != 1:
            return
        if tag in ('td', 'th'):
            self._in_cell = True
            self._current_cell = []
            self._sort_value = None
        elif tag == 'tr':
            self._current_row = []
        elif tag == 'span' and self._in_cell:
            sv = attrdict.get('data-sort-value')
            if sv:
                self._sort_value = sv

    def handle_endtag(self, tag):
        if tag == 'table':
            if self._in_table:
                self._depth -= 1
                if self._depth == 0:
                    self._in_table = False
            return
        if not self._in_table or self._depth != 1:
            return
        if tag in ('td', 'th') and self._in_cell:
            self._in_cell = False
            self._current_row.append(''.join(self._current_cell).strip())
            self._sort_value = None
        elif tag == 'tr':
            if self._current_row:
                self.rows.append(self._current_row)
                self._current_row = []

    def handle_data(self, data):
        if self._in_table and self._in_cell and self._depth == 1:
            self._current_cell.append(data)


def parseKommuner(html_bytes):
    """Parse the Wikipedia API JSON response and return a list of kommune dicts.

    Each dict has keys: Nr, Kommunenavn, Adm. senter, Fylke, Folketall,
    Areal, Målform. Returns an empty list if parsing fails or no rows are
    found. html_bytes may be bytes or str.
    """
    if isinstance(html_bytes, bytes):
        html_bytes = html_bytes.decode('utf-8')

    try:
        data = json.loads(html_bytes)
        html = data['parse']['text']['*']
    except (KeyError, json.JSONDecodeError, ValueError):
        return []

    parser = _TableParser()
    parser.feed(html)

    kommuner = []
    for row in parser.rows:
        # Skip header rows (th cells produce the same text; header rows
        # typically have fewer than 9 cells or contain 'Nr' / 'Kommunenavn')
        if len(row) < 9:
            continue
        nr = row[_COL_NR].strip()
        if not nr.isdigit():
            continue
        kommuner.append({
            'Nr': nr,
            'Kommunenavn': row[_COL_NAVN].strip(),
            'Adm. senter': row[_COL_ADM].strip(),
            'Fylke': row[_COL_FYLKE].strip(),
            'Folketall': row[_COL_FOLKETALL].strip(),
            'Areal': row[_COL_AREAL].strip(),
            'Målform': row[_COL_MALFORM].strip(),
        })
    return kommuner


def searchKommuner(kommuner, search):
    """Return the first matching kommune dict for search, or None.

    Search order:
    1. Exact match by 4-digit number (if search is all digits).
    2. Case-insensitive exact name match.
    3. Case-insensitive prefix match on name.
    4. Case-insensitive substring match on name.
    """
    if search.isdigit():
        for k in kommuner:
            if k['Nr'] == search:
                return k

    lower = search.lower()

    for k in kommuner:
        if k['Kommunenavn'].lower() == lower:
            return k

    for k in kommuner:
        if k['Kommunenavn'].lower().startswith(lower):
            return k

    for k in kommuner:
        if lower in k['Kommunenavn'].lower():
            return k

    return None


def formatKommune(k):
    """Return a formatted IRC reply string for a kommune dict."""
    return (
        f"{k['Nr']} - {k['Kommunenavn']} "
        f"(Adm. senter {k['Adm. senter']}) "
        f"i {k['Fylke']}. "
        f"{k['Folketall']} innbyggere. "
        f"{k['Areal']} km\u00b2. "
        f"M\u00e5lform: {k['M\u00e5lform'].lower()}."
    )


class Kommune(callbacks.Plugin):
    """Looks up Norwegian municipalities (kommuner) from Wikipedia."""
    threaded = True

    def __init__(self, irc):
        super().__init__(irc)
        self._kommuner = None
        self._cacheTime = 0

    def _getKommuner(self):
        """Return the cached municipality list, refreshing if stale."""
        if self._kommuner is None or time.time() - self._cacheTime > CACHE_TTL:
            self.log.info('Kommune: fetching data from Wikipedia')
            data = utils.web.getUrl(WIKIPEDIA_API_URL)
            self._kommuner = parseKommuner(data)
            self._cacheTime = time.time()
        return self._kommuner

    @wrap(['text'])
    @internationalizeDocstring
    def kommune(self, irc, msg, args, search):
        """<kommune>

        Look up a Norwegian municipality by name or number. Use 'random' for a
        random municipality. Data is sourced from Norwegian Wikipedia."""
        try:
            kommuner = self._getKommuner()
        except Exception as e:
            self.log.error('Kommune: failed to fetch data: %s', str(e))
            irc.error(_('Failed to fetch municipality data from Wikipedia.'))
            return

        if not kommuner:
            irc.error(_('No municipality data available.'))
            return

        if search.lower() == 'random':
            irc.reply(formatKommune(random.choice(kommuner)))
            return

        hit = searchKommuner(kommuner, search)
        if hit:
            irc.reply(formatKommune(hit))
        else:
            irc.error(_('No municipality found matching \u2019%s\u2019.') % search)

Class = Kommune
