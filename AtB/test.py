###
# Copyright (c) 2011, Terje Hoås
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

from . import plugin


class AtBHelperTestCase(SupyTestCase):

    def testFetchOracleStripsWhitespace(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'  Berg Bedehus mot sentrum: #75 om ca. 10 min.  '
        try:
            result = plugin.fetchOracle('Berg')
            self.assertEqual(result, 'Berg Bedehus mot sentrum: #75 om ca. 10 min.')
        finally:
            utils.web.getUrl = original

    def testFetchOracleCollapseNewlines(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'Line one\nLine two'
        try:
            result = plugin.fetchOracle('test')
            self.assertEqual(result, 'Line one Line two')
        finally:
            utils.web.getUrl = original


class AtBCommandTestCase(PluginTestCase):
    plugins = ('AtB',)

    def testBussReturnsOracleAnswer(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'Berg Bedehus mot sentrum: #75 om ca. 10 min.'
        try:
            self.assertResponse('buss Berg', 'Berg Bedehus mot sentrum: #75 om ca. 10 min.')
        finally:
            utils.web.getUrl = original

    def testBussErrorOnFailure(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: (_ for _ in ()).throw(Exception('network error'))
        try:
            self.assertError('buss Berg')
        finally:
            utils.web.getUrl = original
