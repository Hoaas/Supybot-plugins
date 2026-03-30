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
from dateutil import parser

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('BadeTemp')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


def fetchTemps(search, data):
    """Return a list of 'temp° name' strings matching search in region name.

    Entries older than 7 days are excluded. data may be a JSON string or
    bytes. search is matched case-insensitively against the region name.
    """
    if isinstance(data, bytes):
        data = data.decode()
    j = json.loads(data)

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    locs = []

    for loc in j:
        location = loc.get('location')
        if location is None:
            continue
        region = location.get('region')
        if region is None:
            continue
        regionName = region.get('name')
        if regionName is None:
            continue
        if search.lower() not in regionName.lower():
            continue

        timeStr = loc.get('time')
        if timeStr is None:
            continue
        reportedDate = parser.isoparse(timeStr)
        if reportedDate.tzinfo is None:
            reportedDate = reportedDate.replace(tzinfo=timezone.utc)
        if reportedDate < cutoff:
            continue

        temp = loc.get('temperature')
        name = location.get('name')
        locs.append(f'{temp}° {name}')

    return locs


class BadeTemp(callbacks.Plugin):
    """Badetemperaturer for Norge fra yr.no"""
    threaded = True

    @wrap(['text'])
    @internationalizeDocstring
    def badetemp(self, irc, msg, args, search):
        """<sted>

        Viser badetemperatur for plasser rundt om i Norge. Data hentes fra
        Yr.no."""
        url = 'https://www.yr.no/api/v0/regions/NO/watertemperatures'
        data = utils.web.getUrl(url)
        locs = fetchTemps(search, data)
        if locs:
            irc.reply(', '.join(locs))
        else:
            irc.reply(_('No regions found with that name'))

Class = BadeTemp

