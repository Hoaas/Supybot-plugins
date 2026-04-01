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

import supybot.utils as utils
from supybot.test import *

from . import plugin as kommune_plugin


# ---------------------------------------------------------------------------
# Fixture helpers
# ---------------------------------------------------------------------------

def makeRow(nr, navn, adm, fylke, folketall, areal, malform):
    """Build a single <tr> with 9 <td> cells matching the Wikipedia table.

    The Folketall and Areal cells use the data-sort-value span pattern from
    the real Wikipedia page. Columns 6 and 7 (Kart / Våpen) are image cells.
    """
    return (
        f'<tr>'
        f'<td>{nr}</td>'
        f'<td>{navn}</td>'
        f'<td>{adm}</td>'
        f'<td>{fylke}</td>'
        f'<td><span data-sort-value="3&amp;503&amp;{folketall.replace("\u00a0", "")}&amp;">'
        f'{folketall}</span></td>'
        f'<td><span data-sort-value="3&amp;503&amp;{areal.replace(",", ".")}&amp;">'
        f'{areal}</span></td>'
        f'<td><img src="kart.svg"/></td>'
        f'<td><img src="vaapen.svg"/></td>'
        f'<td>{malform}</td>'
        f'</tr>'
    )


def makeApiResponse(*rows):
    """Wrap table rows in a Wikipedia API JSON response."""
    header = (
        '<tr>'
        '<th>Nr</th>'
        '<th>Kommunenavn</th>'
        '<th>Adm. senter</th>'
        '<th>Fylke</th>'
        '<th>Folketall</th>'
        '<th>Areal</th>'
        '<th class="unsortable">Kart</th>'
        '<th class="unsortable">V\u00e5pen</th>'
        '<th>M\u00e5lform</th>'
        '</tr>'
    )
    body = ''.join(rows)
    html = f'<table class="wikitable sortable">{header}{body}</table>'
    payload = {'parse': {'text': {'*': html}}}
    return json.dumps(payload).encode('utf-8')


# Two-entry fixture used across many tests
_ROW_OSLO = makeRow('0301', 'Oslo', 'Oslo', 'Oslo',
                    '724\u00a0290', '454,03', 'n\u00f8ytral')
_ROW_BERGEN = makeRow('4601', 'Bergen', 'Bergen', 'Vestland',
                      '288\u00a0198', '465,29', 'bokm\u00e5l')
_ROW_BODO = makeRow('1804', 'Bod\u00f8', 'Bod\u00f8', 'Nordland',
                    '52\u00a0578', '4\u00a0700,09', 'bokm\u00e5l')

FIXTURE_DATA = makeApiResponse(_ROW_OSLO, _ROW_BERGEN, _ROW_BODO)


# ---------------------------------------------------------------------------
# Unit tests for parseKommuner
# ---------------------------------------------------------------------------

class ParseKommunerTestCase(SupyTestCase):

    def testParsesRowsCorrectly(self):
        result = kommune_plugin.parseKommuner(FIXTURE_DATA)
        self.assertEqual(len(result), 3)

    def testFieldValues(self):
        result = kommune_plugin.parseKommuner(FIXTURE_DATA)
        oslo = result[0]
        self.assertEqual(oslo['Nr'], '0301')
        self.assertEqual(oslo['Kommunenavn'], 'Oslo')
        self.assertEqual(oslo['Adm. senter'], 'Oslo')
        self.assertEqual(oslo['Fylke'], 'Oslo')
        self.assertIn('290', oslo['Folketall'])
        self.assertIn('454', oslo['Areal'])
        self.assertEqual(oslo['Målform'], 'nøytral')

    def testAcceptsBytesInput(self):
        result = kommune_plugin.parseKommuner(FIXTURE_DATA)
        self.assertIsInstance(result, list)
        self.assertTrue(len(result) > 0)

    def testAcceptsStringInput(self):
        result = kommune_plugin.parseKommuner(FIXTURE_DATA.decode('utf-8'))
        self.assertEqual(len(result), 3)

    def testInvalidJsonReturnsEmptyList(self):
        result = kommune_plugin.parseKommuner(b'not json at all')
        self.assertEqual(result, [])

    def testMissingParseKeyReturnsEmptyList(self):
        result = kommune_plugin.parseKommuner(json.dumps({}).encode())
        self.assertEqual(result, [])

    def testEmptyTableReturnsEmptyList(self):
        html = '<table class="wikitable sortable"></table>'
        payload = {'parse': {'text': {'*': html}}}
        result = kommune_plugin.parseKommuner(json.dumps(payload).encode())
        self.assertEqual(result, [])

    def testRowsWithNonNumericNrAreSkipped(self):
        # Header row has non-numeric Nr — should be skipped
        html = (
            '<table class="wikitable sortable">'
            '<tr><th>Nr</th><th>Kommunenavn</th><th>Adm. senter</th>'
            '<th>Fylke</th><th>Folketall</th><th>Areal</th>'
            '<th>Kart</th><th>V\u00e5pen</th><th>M\u00e5lform</th></tr>'
            '</table>'
        )
        payload = {'parse': {'text': {'*': html}}}
        result = kommune_plugin.parseKommuner(json.dumps(payload).encode())
        self.assertEqual(result, [])


# ---------------------------------------------------------------------------
# Unit tests for searchKommuner
# ---------------------------------------------------------------------------

def makeKommune(nr, navn, adm='X', fylke='Y', folketall='1 000',
                areal='100,00', malform='bokm\u00e5l'):
    return {
        'Nr': nr,
        'Kommunenavn': navn,
        'Adm. senter': adm,
        'Fylke': fylke,
        'Folketall': folketall,
        'Areal': areal,
        'Målform': malform,
    }


KOMMUNER = [
    makeKommune('0301', 'Oslo', adm='Oslo', fylke='Oslo', malform='nøytral'),
    makeKommune('4601', 'Bergen', adm='Bergen', fylke='Vestland'),
    makeKommune('5001', 'Trondheim', adm='Trondheim', fylke='Trøndelag'),
    makeKommune('1804', 'Bodø', adm='Bodø', fylke='Nordland'),
]


class SearchKommunerTestCase(SupyTestCase):

    def testExactNameMatch(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, 'Oslo')
        self.assertIsNotNone(result)
        self.assertEqual(result['Nr'], '0301')

    def testExactNameMatchCaseInsensitive(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, 'oslo')
        self.assertIsNotNone(result)
        self.assertEqual(result['Nr'], '0301')

    def testExactNameMatchMixedCase(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, 'BERGEN')
        self.assertIsNotNone(result)
        self.assertEqual(result['Nr'], '4601')

    def testNumberMatch(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, '0301')
        self.assertIsNotNone(result)
        self.assertEqual(result['Kommunenavn'], 'Oslo')

    def testPrefixMatch(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, 'Trond')
        self.assertIsNotNone(result)
        self.assertEqual(result['Nr'], '5001')

    def testPrefixMatchCaseInsensitive(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, 'trond')
        self.assertIsNotNone(result)
        self.assertEqual(result['Nr'], '5001')

    def testSubstringMatch(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, 'ndheim')
        self.assertIsNotNone(result)
        self.assertEqual(result['Nr'], '5001')

    def testNoMatchReturnsNone(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, 'Stavanger')
        self.assertIsNone(result)

    def testNumberNoMatchReturnsNone(self):
        result = kommune_plugin.searchKommuner(KOMMUNER, '9999')
        self.assertIsNone(result)

    def testEmptyListReturnsNone(self):
        result = kommune_plugin.searchKommuner([], 'Oslo')
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Unit tests for formatKommune
# ---------------------------------------------------------------------------

class FormatKommuneTestCase(SupyTestCase):

    def testFormatContainsNr(self):
        k = makeKommune('0301', 'Oslo', adm='Oslo', fylke='Oslo',
                        malform='nøytral')
        result = kommune_plugin.formatKommune(k)
        self.assertIn('0301', result)

    def testFormatContainsName(self):
        k = makeKommune('0301', 'Oslo', adm='Oslo', fylke='Oslo',
                        malform='nøytral')
        result = kommune_plugin.formatKommune(k)
        self.assertIn('Oslo', result)

    def testFormatMalformIsLowercased(self):
        k = makeKommune('0301', 'Oslo', malform='Nøytral')
        result = kommune_plugin.formatKommune(k)
        self.assertIn('nøytral', result)
        self.assertNotIn('Nøytral', result)

    def testFormatContainsKm2Symbol(self):
        k = makeKommune('0301', 'Oslo')
        result = kommune_plugin.formatKommune(k)
        self.assertIn('km²', result)

    def testFullFormat(self):
        k = makeKommune('0301', 'Oslo', adm='Oslo', fylke='Oslo',
                        folketall='724 290', areal='454,03',
                        malform='nøytral')
        result = kommune_plugin.formatKommune(k)
        self.assertEqual(
            result,
            '0301 - Oslo (Adm. senter Oslo) i Oslo. '
            '724 290 innbyggere. 454,03 km². Målform: nøytral.'
        )


# ---------------------------------------------------------------------------
# Integration tests for the bot command — network call is mocked
# ---------------------------------------------------------------------------

class KommuneCommandTestCase(PluginTestCase):
    plugins = ('Kommune',)

    def testCommandReturnsMatch(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: FIXTURE_DATA
        try:
            self.assertResponse(
                'kommune Oslo',
                '0301 - Oslo (Adm. senter Oslo) i Oslo. '
                '724\xa0290 innbyggere. 454,03 km\xb2. M\xe5lform: n\xf8ytral.'
            )
        finally:
            utils.web.getUrl = original

    def testCommandNotFound(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: FIXTURE_DATA
        try:
            self.assertError('kommune Stavanger')
        finally:
            utils.web.getUrl = original

    def testCommandByNumber(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: FIXTURE_DATA
        try:
            self.assertResponse(
                'kommune 4601',
                '4601 - Bergen (Adm. senter Bergen) i Vestland. '
                '288\xa0198 innbyggere. 465,29 km\xb2. M\xe5lform: bokm\xe5l.'
            )
        finally:
            utils.web.getUrl = original

    def testCommandPrefixMatch(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: FIXTURE_DATA
        try:
            self.assertResponse(
                'kommune Berg',
                '4601 - Bergen (Adm. senter Bergen) i Vestland. '
                '288\xa0198 innbyggere. 465,29 km\xb2. M\xe5lform: bokm\xe5l.'
            )
        finally:
            utils.web.getUrl = original

    def testCommandRandom(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: FIXTURE_DATA
        try:
            self.assertNotError('kommune random')
        finally:
            utils.web.getUrl = original

    def testCommandFetchError(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: (_ for _ in ()).throw(
            Exception('network error'))
        try:
            self.assertError('kommune Oslo')
        finally:
            utils.web.getUrl = original
