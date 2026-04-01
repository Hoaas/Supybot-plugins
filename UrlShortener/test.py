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

import supybot.conf as conf
import supybot.utils as utils
from supybot.test import *


class UrlShortenerCommandTestCase(ChannelPluginTestCase):
    plugins = ('UrlShortener',)
    # Lower the threshold so test URLs (which would be short) still trigger
    # shortening.
    config = {'supybot.plugins.UrlShortener.length': 0}

    def testDoPrivmsgShortensUrl(self):
        """Feeding a message with a URL should produce a 'Short url:' reply."""
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'https://is.gd/TESTXX'
        try:
            self.feedMsg('check out https://www.example.com/some/very/long/path')
            m = self.getMsg(' ')
            self.assertIsNotNone(m, 'Expected a reply but got none')
            self.assertIn('Short url:', m.args[1])
            self.assertIn('https://is.gd/TESTXX', m.args[1])
        finally:
            utils.web.getUrl = original

    def testDoPrivmsgSilentOnError(self):
        """When the is.gd call raises, the plugin should log and stay silent."""
        original = utils.web.getUrl
        def raise_error(url, **kw):
            raise Exception('network error')
        utils.web.getUrl = raise_error
        try:
            self.feedMsg('check out https://www.example.com/some/very/long/path')
            # Give the threaded handler time; then confirm no reply arrived.
            m = self.irc.takeMsg()
            self.assertIsNone(m, 'Expected no reply on error but got one')
        finally:
            utils.web.getUrl = original

    def testDoPrivmsgNoTriggerBelowThreshold(self):
        """URLs shorter than the threshold should not be shortened."""
        original = utils.web.getUrl
        called = []
        utils.web.getUrl = lambda url, **kw: called.append(url) or b'https://is.gd/X'
        # Restore threshold to default (170) so a short URL won't trigger.
        try:
            with conf.supybot.plugins.UrlShortener.length.context(170):
                self.feedMsg('see http://x.co/short')
                m = self.irc.takeMsg()
                self.assertIsNone(m, 'Expected no reply for short URL')
                self.assertEqual(called, [], 'getUrl should not be called for short URL')
        finally:
            utils.web.getUrl = original
