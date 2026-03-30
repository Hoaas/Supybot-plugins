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
    _ = PluginInternationalization('Olympics')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class Olympics(callbacks.Plugin):
    """Shows medal winners for the Olympics."""
    threaded = True

    url = "https://www.olympics.com/wmr-owg2026/competition/api/ENG/medals"

    @wrap
    def medals(self, irc, msg, args):
        """
        Return top medal winners."""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/json',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://www.olympics.com/'
            }
            data = utils.web.getUrl(self.url, headers=headers).decode()
            
            m = json.loads(data)
            
            # Extract medals data from the API response
            medal_standings = m.get('medalStandings', {})
            
            # medalStandings is a dict with 'medalsTable' containing the list of countries
            all_countries = []
            if isinstance(medal_standings, dict):
                for key in medal_standings.keys():
                    value = medal_standings[key]
                    if isinstance(value, list):
                        all_countries = value
                        break
            
            # Sort by the official rank field from the API
            sortedlist = sorted(all_countries, key=lambda k: k.get('rank', 999))
            
            # Display top 5 countries
            for i, country in enumerate(sortedlist[:5], 1):
                irc.reply(self.createReply(country, i))
        except Exception as e:
            irc.error(f"Error: {type(e).__name__}: {str(e)}")

    def getTotalMedals(self, country):
        """Extract total medals for a country."""
        medals_number = country.get('medalsNumber', [])
        for medal_entry in medals_number:
            if medal_entry.get('type') == 'Total':
                return (medal_entry.get('gold', 0), medal_entry.get('silver', 0), medal_entry.get('bronze', 0))
        return (0, 0, 0)

    def getMedalCounts(self, country, *keys):
        """Extract medal counts from medalsNumber array for sorting."""
        medals_number = country.get('medalsNumber', [])
        total_medals = {}
        for medal_entry in medals_number:
            if medal_entry.get('type') == 'Total':
                total_medals = medal_entry
                break
        return tuple(total_medals.get(key, 0) for key in keys)

    def createReply(self, country, place):
        # Extract total medals from medalsNumber array
        medals_number = country.get('medalsNumber', [])
        total_medals = {}
        for medal_entry in medals_number:
            if medal_entry.get('type') == 'Total':
                total_medals = medal_entry
                break
        
        gold = total_medals.get('gold', 0)
        silver = total_medals.get('silver', 0)
        bronze = total_medals.get('bronze', 0)
        total = total_medals.get('total', 0)
        
        formattedString = "{}. {} - 🥇{} 🥈{} 🥉{} (Total: {})".format(
            place,
            country.get("description", "Unknown"),
            gold,
            silver,
            bronze,
            total
        )
        return formattedString

Class = Olympics
