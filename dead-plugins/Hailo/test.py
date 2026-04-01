###
# Copyright (c) 2010, Nicolas Coevoet
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

from supybot.test import *

from . import plugin as hailo_plugin


class HailoHelperTestCase(SupyTestCase):
    """Tests for the module-level sanitize() helper (no bot required)."""

    def testSanitizeRemovesDangerousChars(self):
        result = hailo_plugin.sanitize('hello `world`')
        self.assertEqual(result, 'hello world')

    def testSanitizeRemovesPipe(self):
        result = hailo_plugin.sanitize('cat /etc/passwd | grep root')
        self.assertEqual(result, 'cat /etc/passwd  grep root')

    def testSanitizeRemovesAmpersand(self):
        result = hailo_plugin.sanitize('foo & bar')
        self.assertEqual(result, 'foo  bar')

    def testSanitizeRemovesRedirection(self):
        result = hailo_plugin.sanitize('echo foo > /tmp/x')
        self.assertEqual(result, 'echo foo  /tmp/x')

    def testSanitizeRemovesSemicolon(self):
        result = hailo_plugin.sanitize('echo foo; rm -rf /')
        self.assertEqual(result, 'echo foo rm -rf /')

    def testSanitizeRemovesQuotes(self):
        result = hailo_plugin.sanitize('say "hello"')
        self.assertEqual(result, 'say hello')

    def testSanitizePlainString(self):
        result = hailo_plugin.sanitize('hello world')
        self.assertEqual(result, 'hello world')

    def testSanitizeEmptyString(self):
        result = hailo_plugin.sanitize('')
        self.assertEqual(result, '')

    def testSanitizeAllDangerousChars(self):
        result = hailo_plugin.sanitize('`|&>;<"')
        self.assertEqual(result, '')


class HailoCommandTestCase(PluginTestCase):
    """Bot-level tests for the Hailo plugin.

    NOTE: Full command testing (hailo, brainstats) requires the `hailo`
    markov binary to be installed and a populated database. Only the
    help text is verified here.
    """
    plugins = ('Hailo',)

    def testBrainstatsHelp(self):
        self.assertRegexp('help brainstats', 'takes no arguments')

    def testHailoHelp(self):
        self.assertHelp('hailo')
