###
# Copyright (c) 2018, Terje Hoås
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

from .plugin import hashPassword, parseHibpResponse


# SHA1('test')  = A94A8FE5CCB19BA61C4C0873D391E987982FBBD3
#   prefix = a94a8   suffix = FE5CCB19BA61C4C0873D391E987982FBBD3
# SHA1('password') = 5BAA61E4C9B93F3F0682250B6CF8331B7EE68FD8
#   prefix = 5baa6   suffix = 1E4C9B93F3F0682250B6CF8331B7EE68FD8

_HIBP_TEST_FIXTURE = (
    b'FE5CCB19BA61C4C0873D391E987982FBBD3:42\r\n'
    b'AABBCCDDEEFF00112233445566778899000:1\r\n'
)

_HIBP_PASSWORD_FIXTURE = (
    b'1E4C9B93F3F0682250B6CF8331B7EE68FD8:3730471\r\n'
    b'AABBCCDDEEFF00112233445566778899000:1\r\n'
)


class PasswordTesterHelperTestCase(SupyTestCase):

    def testHashPasswordPrefix(self):
        prefix, suffix = hashPassword('test')
        self.assertEqual(prefix, 'a94a8')

    def testHashPasswordSuffix(self):
        prefix, suffix = hashPassword('test')
        self.assertEqual(suffix, 'FE5CCB19BA61C4C0873D391E987982FBBD3')

    def testHashPasswordKnownPassword(self):
        prefix, suffix = hashPassword('password')
        self.assertEqual(prefix, '5baa6')
        self.assertEqual(suffix, '1E4C9B93F3F0682250B6CF8331B7EE68FD8')

    def testParseHibpResponseFound(self):
        text = 'FE5CCB19BA61C4C0873D391E987982FBBD3:42\r\nAABBCC:1\r\n'
        count = parseHibpResponse(text, 'FE5CCB19BA61C4C0873D391E987982FBBD3')
        self.assertEqual(count, 42)

    def testParseHibpResponseNotFound(self):
        text = 'AABBCCDDEEFF00112233445566778899000:99\r\n'
        count = parseHibpResponse(text, 'FE5CCB19BA61C4C0873D391E987982FBBD3')
        self.assertEqual(count, 0)

    def testParseHibpResponseCaseInsensitive(self):
        text = 'fe5ccb19ba61c4c0873d391e987982fbbd3:7\r\n'
        count = parseHibpResponse(text, 'FE5CCB19BA61C4C0873D391E987982FBBD3')
        self.assertEqual(count, 7)

    def testParseHibpResponseMalformedLine(self):
        # A line without ':' should be silently skipped.
        text = 'NOSEPARATOR\r\nFE5CCB19BA61C4C0873D391E987982FBBD3:3\r\n'
        count = parseHibpResponse(text, 'FE5CCB19BA61C4C0873D391E987982FBBD3')
        self.assertEqual(count, 3)

    def testParseHibpResponseEmptyResponse(self):
        count = parseHibpResponse('', 'FE5CCB19BA61C4C0873D391E987982FBBD3')
        self.assertEqual(count, 0)


class PasswordTesterCommandTestCase(PluginTestCase):
    plugins = ('PasswordTester',)

    def testPasswordPwned(self):
        # SHA1('test') suffix matches the fixture with count 42.
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: _HIBP_TEST_FIXTURE
        try:
            self.assertRegexp('password test', r'42 times')
        finally:
            utils.web.getUrl = original

    def testPasswordSafe(self):
        # Return a fixture that does NOT contain the suffix for 'test'.
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'AABBCCDDEEFF00112233445566778899000:1\r\n'
        try:
            self.assertRegexp('password test', r'not been seen')
        finally:
            utils.web.getUrl = original

    def testPasswordHighCount(self):
        # SHA1('password') appears 3 730 471 times per the fixture.
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: _HIBP_PASSWORD_FIXTURE
        try:
            self.assertRegexp('password password', r'3730471 times')
        finally:
            utils.web.getUrl = original

    def testPasswordNetworkError(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: (_ for _ in ()).throw(IOError('network down'))
        try:
            self.assertRegexp('password test', r'HIBP failed')
        finally:
            utils.web.getUrl = original
