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

from supybot.test import *

from . import plugin as navnedag_plugin


class NavnedagHelperTestCase(SupyTestCase):
    def testNewYearsDay(self):
        info = navnedag_plugin.namedata['01-01']
        self.assertIn('Jesus', info[0])

    def testChristmasDay(self):
        info = navnedag_plugin.namedata['12-25']
        self.assertIn('juledag', info[0])

    def testDecember26(self):
        info = navnedag_plugin.namedata['12-26']
        self.assertIn('Stefan', info[0])

    def testEntryHasAtLeastOneName(self):
        for key, value in navnedag_plugin.namedata.items():
            self.assertTrue(len(value) >= 1, f'Entry for {key} has no name')

    def testMissingDateRaisesKeyError(self):
        with self.assertRaises(KeyError):
            _ = navnedag_plugin.namedata['00-00']


class NavnedagCommandTestCase(PluginTestCase):
    plugins = ('Navnedag',)

    def testNavnedagNoError(self):
        self.assertNotError('navnedag')

    def testNavnedagReturnsName(self):
        self.assertRegexp('navnedag', r'\w+')
