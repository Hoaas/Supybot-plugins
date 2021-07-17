###
# Copyright (c) 2017, Terje Hoås
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
from datetime import datetime, timedelta, timezone
from dateutil import tz, parser

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('BadeTemp')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class BadeTemp(callbacks.Plugin):
    """Badetemperaturer for Norge fra yr.no"""
    threaded = True

    @wrap(['text'])
    def badetemp(self, irc, msg, args, search):
        """
        Viser badetemperatur for plasser rundt om i Norge. Data hentes fra Yr.no."""

        url = "https://www.yr.no/api/v0/regions/NO/watertemperatures"
        text = utils.web.getUrl(url).decode()
        j = json.loads(text)

        locs = []

        last_week = datetime.now() - timedelta(days=7)

        for loc in j:
            location = loc.get('location')
            if location is None:
                continue
            region = location.get('region')
            if region is None:
                continue
            name = region.get('name')
            if name is None:
                continue
            names = name.lower()
            if search.lower() in names:
                time = loc.get('time')
                reported_date = parser.isoparse(time).replace(tzinfo=None)

                if reported_date < last_week:
                    continue

                temp = loc.get('temperature')
                name = loc.get('location').get('name')
                locs.append('{0}° {1}'.format(temp, name))
        if locs is None or len(locs) == 0:
            irc.reply('Fant ingen regioner med det navnet')
        else:
            irc.reply(', '.join(locs))

Class = BadeTemp
