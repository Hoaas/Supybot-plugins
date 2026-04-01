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

import supybot.utils as utils
from supybot.test import *

# Fixture HTML for whatthefuckshouldimakefordinner.com
# The parser does:
#   1. find '<dl>' -> skip 4 chars -> read until '</dl>' = insult
#   2. find next '<dl>' -> find '<a href="' -> skip 9 chars -> read until '"' = dinnerurl
#   3. find '>' -> skip 1 char -> read until '</a>' = dinner name
DINNER_HTML = b"""<html><body>
<dl>How about some fucking</dl>
<dl><a href="http://example.com/spaghetti">Spaghetti Bolognese</a></dl>
</body></html>"""


class WTFSIMFDHelperTestCase(SupyTestCase):
    """Tests for HTML parsing logic used by the WTFSIMFD plugin."""

    def testDinnerParsing(self):
        html = DINNER_HTML.decode(errors='ignore')
        html = html[html.find('<dl>')+4:]
        insult = html[:html.find('</dl>')].strip()
        self.assertEqual(insult, 'How about some fucking')

    def testDinnerUrlParsing(self):
        html = DINNER_HTML.decode(errors='ignore')
        html = html[html.find('<dl>')+4:]
        # skip insult block
        html = html[html.find('<dl>')+4:]
        html = html[html.find('<a href="')+9:]
        dinnerurl = html[:html.find('"')].strip()
        self.assertEqual(dinnerurl, 'http://example.com/spaghetti')

    def testDinnerNameParsing(self):
        html = DINNER_HTML.decode(errors='ignore')
        html = html[html.find('<dl>')+4:]
        html = html[html.find('<dl>')+4:]
        html = html[html.find('<a href="')+9:]
        html = html[html.find('>')+1:]
        dinner = html[:html.find('</a>')].strip()
        self.assertEqual(dinner, 'Spaghetti Bolognese')


class WTFSIMFDCommandTestCase(PluginTestCase):
    plugins = ('WTFSIMFD',)

    def testDinner(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: DINNER_HTML
        try:
            self.assertRegexp('dinner', r'How about some fucking Spaghetti Bolognese\. \(http://example\.com/spaghetti\)')
        finally:
            utils.web.getUrl = original
