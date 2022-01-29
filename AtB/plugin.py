# coding=utf8
###
# Copyright (c) 2011, Terje Hoås
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
import urllib.request, urllib.parse, urllib.error
import urllib.request, urllib.error, urllib.parse
import json
import datetime
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class AtB(callbacks.Plugin):
    """Returns real time data on next passing on busses in Trondheim. 
    Gets data from BusBuddy API (http://api.busbuddy.norrs.no:8080/) which is supplied unofficially from AtB (atb.no).
    Also calculate it the price for a season card."""
    threaded = True
    
    def buss(self, irc, msg, args, text):
        """<tekst>
        Returnerer tekst fra bussorakelet i Trondheim.
        """
        #url = 'http://busstuc-atb.lingit.no/json.php?callback=bussOrakel&question='
        #url = 'https://www.atb.no/xmlhttprequest.php?service=routeplannerOracle.getOracleAnswer&question='
        url = 'http://busstjener.idi.ntnu.no/busstuc/oracle?q='
        url += urllib.parse.quote(text)
        data = utils.web.getUrl(url).decode()
        data = data.strip()
        data = data.replace('\n', ' ')

        irc.reply(data)

    buss = wrap(buss, ['text'])

Class = AtB


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
