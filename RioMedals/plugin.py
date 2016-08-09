###
# Copyright (c) 2016, Terje Hoås
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
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('RioMedals')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class RioMedals(callbacks.Plugin):
    """Shows medal winners for Rio Olympics 2016. Uses http://www.medalbot.com/."""
    threaded = True

    url = "http://www.medalbot.com/api/v1/medals"

    @wrap
    def medals(self, irc, msg, args):
        """
        Return top medal winners."""
        data = utils.web.getUrl(self.url).decode()
        m = json.loads(data)
        sortedlist = sorted(m, key= lambda k: k['place'])
        counter = 0
        for country in sortedlist:
            if (counter >= 5):
                break
            irc.reply(self.createReply(country))
            counter += 1

        for country in sortedlist:
            if country.get("country_name") == 'Norway':
                irc.reply(self.createReply(country))
                return
        dummyCountry = {
                "id": "norway", 
                "country_name": "Norway",
                "gold_count": 0, 
                "silver_count": 0, 
                "bronze_count": 0, 
                "place": "??", 
                "total_count": 0
            }
        irc.reply(self.createReply(dummyCountry))

    def createReply(self, country):
        formattedString = "{:2} - {:15} G:{:2}, S:{:2}, B:{:2}. Total: {:2}.".format(
            country.get("place"),
            country.get("country_name"),
            country.get("gold_count"),
            country.get("silver_count"),
            country.get("bronze_count"),
            country.get("total_count")
        )
        return formattedString

Class = RioMedals
