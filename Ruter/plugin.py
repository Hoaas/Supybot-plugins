# coding=utf8
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
import re
import json
import urllib.request, urllib.parse, urllib.error
import datetime

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Ruter')

@internationalizeDocstring
class Ruter(callbacks.Plugin):
    """Add the help for "@plugin help Ruter" here
    This should describe *how* to use this plugin."""
    threaded = True

    baseurl = 'http://api-test.trafikanten.no/'

    def search(self, place):
        url = self.baseurl + 'RealTime/FindMatches/' + urllib.parse.quote(place)
        data = utils.web.getUrl(url).decode()
        j = json.loads(data)

        return j[0].get('ID')

    def get_real_time_data(self, loc):
        url = self.baseurl + 'RealTime/GetRealTimeData/' + urllib.parse.quote(str(loc))
        data = utils.web.getUrl(url).decode()
        j = json.loads(data)
        date1 = j[0].get('ExpectedArrivalTime')
        direction1 = j[0].get('DestinationName')
        date2 = j[1].get('ExpectedArrivalTime')
        direction2 = j[1].get('DestinationName')
        pattern = r'\d+'
        epoch1 = re.search(pattern, date1).group()
        epoch2 = re.search(pattern, date2).group()
        return int(str(epoch1)[:-3]), direction1, int(str(epoch2)[:-3]), direction2, 

    def ruter(self, irc, msg, args, place):
        """<boop>
        
        :D"""
        loc = self.search(place)
        time1, dir1, time2, dir2 = self.get_real_time_data(loc)
        t1 = datetime.datetime.fromtimestamp(time1)
        t2 = datetime.datetime.fromtimestamp(time2)
        irc.reply('Retning ' + str(dir1) + ': ' + str(t1))
        irc.reply('Retning ' + str(dir2) + ': ' + str(t2))
    ruter = wrap(ruter, ['text'])

Class = Ruter


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
