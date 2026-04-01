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

import supybot.utils as utils
from supybot.test import *

from . import plugin as ssb_plugin


def makeDoc(count, gender, type_, name):
    """Build a single nameSearch doc entry."""
    return {'count': count, 'gender': gender, 'type': type_, 'name': name}


def makeData(*docs):
    """Serialise a nameSearch response with the given docs to JSON bytes."""
    return json.dumps({'response': {'docs': list(docs)}}).encode()


# ---------------------------------------------------------------------------
# Unit tests for the formatNameResults helper — no bot, no network
# ---------------------------------------------------------------------------

class SSBHelperTestCase(SupyTestCase):

    def testLastName(self):
        data = makeData(makeDoc(186, '-', 'family', 'HOÅS'))
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(result, 'HOÅS: 186 last name')

    def testFirstNameOnly(self):
        data = makeData(makeDoc(15782, 'M', 'onlygiven', 'TERJE'))
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(result, 'TERJE: 15782 first name (only) (M)')

    def testFirstNameWithMiddleName(self):
        data = makeData(makeDoc(18994, 'M', 'firstgiven', 'TERJE'))
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(result, 'TERJE: 18994 first name (with middle name) (M)')

    def testMiddleAndFamilyName(self):
        data = makeData(makeDoc(109, '-', 'middleandfamily', 'HOÅS'))
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(result, 'HOÅS: 109 middle + last name')

    def testFemaleFirstName(self):
        data = makeData(makeDoc(4200, 'F', 'onlygiven', 'ANNE'))
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(result, 'ANNE: 4200 first name (only) (F)')

    def testGroupingSameNameTogether(self):
        # Two docs for HOÅS should appear in one group, pipe-separated from TERJE.
        data = makeData(
            makeDoc(186, '-', 'family', 'HOÅS'),
            makeDoc(18994, 'M', 'firstgiven', 'TERJE'),
            makeDoc(15782, 'M', 'onlygiven', 'TERJE'),
            makeDoc(109, '-', 'middleandfamily', 'HOÅS'),
        )
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(
            result,
            'HOÅS: 186 last name, 109 middle + last name'
            ' | TERJE: 18994 first name (with middle name) (M), 15782 first name (only) (M)',
        )

    def testEmptyDocsReturnsNone(self):
        data = json.dumps({'response': {'docs': []}}).encode()
        result = ssb_plugin.formatNameResults(data)
        self.assertIsNone(result)

    def testMissingResponseKeyReturnsNone(self):
        data = json.dumps({}).encode()
        result = ssb_plugin.formatNameResults(data)
        self.assertIsNone(result)

    def testAcceptsBytesInput(self):
        data = makeData(makeDoc(100, 'M', 'onlygiven', 'TERJE'))
        self.assertIsInstance(data, bytes)
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(result, 'TERJE: 100 first name (only) (M)')

    def testAcceptsStringInput(self):
        data = makeData(makeDoc(100, 'M', 'onlygiven', 'TERJE')).decode()
        self.assertIsInstance(data, str)
        result = ssb_plugin.formatNameResults(data)
        self.assertEqual(result, 'TERJE: 100 first name (only) (M)')


# ---------------------------------------------------------------------------
# Integration tests for the bot command — network call is mocked
# ---------------------------------------------------------------------------

class SSBCommandTestCase(PluginTestCase):
    plugins = ('SSB',)

    def testCommandReturnsResult(self):
        data = makeData(makeDoc(18994, 'M', 'firstgiven', 'TERJE'))
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse('navn Terje', 'TERJE: 18994 first name (with middle name) (M)')
        finally:
            utils.web.getUrl = original

    def testCommandGroupsMultipleResults(self):
        data = makeData(
            makeDoc(186, '-', 'family', 'HOÅS'),
            makeDoc(18994, 'M', 'firstgiven', 'TERJE'),
            makeDoc(15782, 'M', 'onlygiven', 'TERJE'),
            makeDoc(109, '-', 'middleandfamily', 'HOÅS'),
        )
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse(
                'navn Terje Hoås',
                'HOÅS: 186 last name, 109 middle + last name'
                ' | TERJE: 18994 first name (with middle name) (M), 15782 first name (only) (M)',
            )
        finally:
            utils.web.getUrl = original

    def testCommandReturnsNotFoundMessage(self):
        data = json.dumps({'response': {'docs': []}}).encode()
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: data
        try:
            self.assertResponse('navn Xyzzy', 'No results found for that name')
        finally:
            utils.web.getUrl = original
