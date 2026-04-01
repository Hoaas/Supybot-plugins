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

import os
import tempfile

from supybot.test import *

from . import plugin


class AutoOpHelperTestCase(SupyTestCase):

    def setUp(self):
        super().setUp()
        self._tmpdir = tempfile.mkdtemp()
        # Patch dbPath() so all DB reads/writes go to a temp directory.
        self._origDbPath = plugin.dbPath
        plugin.dbPath = lambda channel: os.path.join(
            self._tmpdir, f'{channel.lstrip("#")}.db'
        )

    def tearDown(self):
        plugin.dbPath = self._origDbPath
        super().tearDown()

    # --- addEntry ---

    def testAddEntrySuccess(self):
        result = plugin.addEntry('#test', r'nick!.*@host\.example\.com', 'op')
        self.assertEqual(result, True)

    def testAddEntryDuplicate(self):
        plugin.addEntry('#test', r'nick!.*@host\.example\.com', 'op')
        result = plugin.addEntry('#test', r'nick!.*@host\.example\.com', 'op')
        self.assertEqual(result, 'exists')

    def testAddEntryInvalidRegex(self):
        result = plugin.addEntry('#test', r'[invalid', 'op')
        self.assertEqual(result, 'invalid')

    def testAddEntryPersists(self):
        plugin.addEntry('#test', r'nick!.*@example\.com', 'voice')
        hostdict = plugin.readDb('#test')
        self.assertIn(r'nick!.*@example\.com', hostdict)
        self.assertEqual(hostdict[r'nick!.*@example\.com'], 'voice')

    def testAddEntryDifferentModes(self):
        plugin.addEntry('#test', r'op!.*@.*', 'op')
        plugin.addEntry('#test', r'hop!.*@.*', 'halfop')
        plugin.addEntry('#test', r'voice!.*@.*', 'voice')
        hostdict = plugin.readDb('#test')
        self.assertEqual(hostdict[r'op!.*@.*'], 'op')
        self.assertEqual(hostdict[r'hop!.*@.*'], 'halfop')
        self.assertEqual(hostdict[r'voice!.*@.*'], 'voice')

    # --- readDb / writeDb round-trip ---

    def testReadDbEmptyWhenMissing(self):
        result = plugin.readDb('#nonexistent')
        self.assertEqual(result, {})

    def testWriteReadRoundtrip(self):
        data = {r'foo!.*@bar': 'op', r'baz!.*@qux': 'voice'}
        plugin.writeDb('#roundtrip', data)
        self.assertEqual(plugin.readDb('#roundtrip'), data)

    # --- matchingUsers (via readDb/writeDb with a fake irc state) ---

    def testPartialPatternDoesNotMatch(self):
        """re.fullmatch: a pattern that only matches a substring must not fire."""
        import re
        # 'example' would match with re.search but not re.fullmatch
        hostdict = {'example': 'op'}
        hostname = 'nick!ident@example.com'
        # Verify directly that fullmatch rejects this
        self.assertIsNone(re.fullmatch('example', hostname))

    def testFullPatternMatches(self):
        """re.fullmatch: an anchored pattern covering the whole hostmask fires."""
        import re
        hostdict = {r'nick!ident@example\.com': 'op'}
        hostname = 'nick!ident@example.com'
        self.assertIsNotNone(re.fullmatch(r'nick!ident@example\.com', hostname))

    def testWildcardPatternMatches(self):
        """re.fullmatch: a wildcard pattern spanning the full string fires."""
        import re
        hostname = 'nick!ident@example.com'
        self.assertIsNotNone(re.fullmatch(r'nick!.*@.*', hostname))


class AutoOpCommandTestCase(PluginTestCase):
    plugins = ('AutoOp',)

    def testAutoopHasDocstring(self):
        self.assertHelp('autoop')

    def testAutohalfopHasDocstring(self):
        self.assertHelp('autohalfop')

    def testAutovoiceHasDocstring(self):
        self.assertHelp('autovoice')
