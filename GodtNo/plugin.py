###
# Copyright (c) 2022, Terje Hoås
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

from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('GodtNo')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class GodtNo(callbacks.Plugin):
    """Get random dinner recipe from godt.no - Norwegian only"""
    threaded = True

    @wrap([])
    def middag(self, irc, msg, args):
        """Henter tilfeldig middag fra godt.no
        """
        url = 'https://www.godt.no/api/graphql?operationName=randomRecipe&variables=%7B%22input%22%3A%7B%22filter%22%3A%5B%7B%22field%22%3A%22status%22%2C%22value%22%3A%22published%22%7D%2C%7B%22field%22%3A%22tag_id%22%2C%22value%22%3A133%7D%5D%7D%7D&extensions=%7B%22persistedQuery%22%3A%7B%22version%22%3A1%2C%22sha256Hash%22%3A%22a3c1210eb33c7eb2eb9cbd1d102450ddf078e50740af9d9eb87c48a1761763e1%22%7D%7D'

        headers = {
            'User-Agent': 'https://github.com/Hoaas/Supybot-plugins'
        }

        data = utils.web.getUrl(url, headers=headers)
        j = json.loads(data)
        randomRecipe = j.get('data').get('randomRecipe')
        title = randomRecipe.get('title').strip()
        time = randomRecipe.get('preparationTime')
        relativeUrl = randomRecipe.get('links').get('relativeUrl')

        irc.reply('%s (%d minutter) - https://godt.no%s' % (title, time, relativeUrl))
        

Class = GodtNo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
