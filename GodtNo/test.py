###
# Copyright (c) 2022, Terje Hoås
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

from . import plugin as godtno_plugin


def makeRecipe(title, cookingTime=30, relativeUrl='/oppskrifter/test-rett'):
    """Build a godt.no GraphQL response payload as bytes."""
    return json.dumps({
        'data': {
            'randomRecipe': {
                'id': '1',
                'title': title,
                'cookingTime': cookingTime,
                'links': {'relativeUrl': relativeUrl},
            }
        }
    }).encode()


# ---------------------------------------------------------------------------
# Unit tests for the formatRecipe helper — no bot, no network
# ---------------------------------------------------------------------------

class FormatRecipeTestCase(SupyTestCase):

    def testReturnsFormattedStringWithTime(self):
        data = makeRecipe('Pasta Carbonara', cookingTime=25,
                          relativeUrl='/oppskrifter/pasta-carbonara')
        result = godtno_plugin.formatRecipe(data)
        self.assertEqual(result,
                         'Pasta Carbonara (25 minutter) - https://godt.no/oppskrifter/pasta-carbonara')

    def testOmitsTimeWhenCookingTimeIsNone(self):
        data = makeRecipe('Pasta Carbonara', cookingTime=None,
                          relativeUrl='/oppskrifter/pasta-carbonara')
        result = godtno_plugin.formatRecipe(data)
        self.assertEqual(result,
                         'Pasta Carbonara - https://godt.no/oppskrifter/pasta-carbonara')

    def testStripsWhitespaceFromTitle(self):
        data = makeRecipe('  Tomatsuppe  ', cookingTime=20,
                          relativeUrl='/oppskrifter/tomatsuppe')
        result = godtno_plugin.formatRecipe(data)
        self.assertEqual(result,
                         'Tomatsuppe (20 minutter) - https://godt.no/oppskrifter/tomatsuppe')

    def testAcceptsBytesInput(self):
        data = makeRecipe('Pasta', cookingTime=20)
        self.assertIsInstance(data, bytes)
        result = godtno_plugin.formatRecipe(data)
        self.assertIsNotNone(result)

    def testAcceptsStringInput(self):
        data = makeRecipe('Pasta', cookingTime=20).decode()
        self.assertIsInstance(data, str)
        result = godtno_plugin.formatRecipe(data)
        self.assertIsNotNone(result)

    def testReturnsNoneWhenRandomRecipeIsNull(self):
        data = json.dumps({'data': {'randomRecipe': None}}).encode()
        result = godtno_plugin.formatRecipe(data)
        self.assertIsNone(result)

    def testReturnsNoneWhenDataKeyMissing(self):
        data = json.dumps({'errors': [{'message': 'PersistedQueryNotFound'}]}).encode()
        result = godtno_plugin.formatRecipe(data)
        self.assertIsNone(result)


# ---------------------------------------------------------------------------
# Integration tests for the bot command — network call is mocked
# ---------------------------------------------------------------------------

class GodtNoCommandTestCase(PluginTestCase):
    plugins = ('GodtNo',)

    def testCommandReturnsRecipeWithTime(self):
        data = makeRecipe('Pasta Carbonara', cookingTime=25,
                          relativeUrl='/oppskrifter/pasta-carbonara')
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse(
                'middag',
                'Pasta Carbonara (25 minutter) - https://godt.no/oppskrifter/pasta-carbonara'
            )
        finally:
            utils.web.getUrl = original

    def testCommandReturnsRecipeWithoutTime(self):
        data = makeRecipe('Tomatsuppe', cookingTime=None,
                          relativeUrl='/oppskrifter/tomatsuppe')
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse(
                'middag',
                'Tomatsuppe - https://godt.no/oppskrifter/tomatsuppe'
            )
        finally:
            utils.web.getUrl = original

    def testCommandReturnsErrorOnBadResponse(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: json.dumps(
            {'data': {'randomRecipe': None}}).encode()
        try:
            self.assertError('middag')
        finally:
            utils.web.getUrl = original

    def testCommandReturnsErrorOnNetworkFailure(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: (_ for _ in ()).throw(
            Exception('connection refused'))
        try:
            self.assertError('middag')
        finally:
            utils.web.getUrl = original
