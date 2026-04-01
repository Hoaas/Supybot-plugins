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

from datetime import date

from supybot.test import *

from . import plugin as weekPlugin


class WeekHelperTestCase(SupyTestCase):
    """Unit tests for the weekStartDate module-level helper function."""

    def testMondayWeek1_2024(self):
        # 2024-01-01 is week 1, and the Monday of that week is 2024-01-01
        result = weekPlugin.weekStartDate(2024, 1)
        self.assertEqual(result, date(2024, 1, 1))

    def testSundayInWeek(self):
        # The end of week 1 2024 should be 2024-01-07 (Sunday)
        start = weekPlugin.weekStartDate(2024, 1)
        from datetime import timedelta
        end = start + timedelta(6)
        self.assertEqual(end, date(2024, 1, 7))

    def testWeek10_2024(self):
        # Week 10 of 2024 starts on Monday 2024-03-04
        result = weekPlugin.weekStartDate(2024, 10)
        self.assertEqual(result, date(2024, 3, 4))

    def testWeek52_2020(self):
        # 2020 has 53 ISO weeks; week 52 starts 2020-12-21
        result = weekPlugin.weekStartDate(2020, 52)
        self.assertEqual(result, date(2020, 12, 21))

    def testWeek53_2020(self):
        # 2020 week 53 starts 2020-12-28
        result = weekPlugin.weekStartDate(2020, 53)
        self.assertEqual(result, date(2020, 12, 28))

    def testWeek1_2015(self):
        # 2015-01-01 is in week 1; Monday of that week is 2014-12-29
        result = weekPlugin.weekStartDate(2015, 1)
        self.assertEqual(result, date(2014, 12, 29))


class WeekCommandTestCase(PluginTestCase):
    plugins = ('Week',)

    def testWeekNoArgs(self):
        self.assertNotError('week')

    def testWeekResponseIsNumber(self):
        self.assertRegexp('week', r'^\d+$')

    def testWeekWithNumber(self):
        self.assertRegexp('week 10', r'^\d{4}-\d{2}-\d{2} - \d{4}-\d{2}-\d{2}$')

    def testWeekWithNumberNotError(self):
        self.assertNotError('week 1')
