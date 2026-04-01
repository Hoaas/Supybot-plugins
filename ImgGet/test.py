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

from supybot.test import *

from . import plugin as imgget_plugin


class ImgGetHelperTestCase(SupyTestCase):
    """Unit tests for pure helper functions that need no IRC context."""

    def setUp(self):
        # Call sizeof_fmt as an unbound method (it takes self + num).
        self._fmt = imgget_plugin.ImgGet.sizeof_fmt

    def testSizeofFmtNone(self):
        self.assertEqual(self._fmt(None, None), 'Unknown size')

    def testSizeofFmtBytes(self):
        self.assertEqual(self._fmt(None, 512), '512.0 bytes')

    def testSizeofFmtKiB(self):
        self.assertEqual(self._fmt(None, 1024), '1.0 KiB')

    def testSizeofFmtMiB(self):
        self.assertEqual(self._fmt(None, 1024 * 1024), '1.0 MiB')

    def testSizeofFmtGiB(self):
        self.assertEqual(self._fmt(None, 1024 ** 3), '1.0 GiB')

    def testSizeofFmtTiB(self):
        self.assertEqual(self._fmt(None, 1024 ** 4), '1.0 TiB')

    def testSizeofFmtStringInput(self):
        # Should coerce string '2048' to int correctly.
        self.assertEqual(self._fmt(None, '2048'), '2.0 KiB')


class ImgGetCommandTestCase(PluginTestCase):
    plugins = ('ImgGet',)

    def testPluginLoads(self):
        # The plugin has no user-facing commands (only doPrivmsg);
        # confirm it loads without error by listing plugins.
        self.assertNotError('list')
