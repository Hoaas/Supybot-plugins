###
# Copyright (c) 2023, Terje Hoås
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

import requests

from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
from supybot.i18n import PluginInternationalization


_ = PluginInternationalization('Fotball')


class Fotball(callbacks.Plugin):
    """Henter siste match details fra NIFS"""
    threaded = True

    @wrap(['text'])
    def fotball(self, irc, msg, args, search):
        """<lag>
        
        Henter siste event i feeden til NIFS der matchnavn inneholder søkeord"""

        url = 'https://v3api.nifs.no/matchEvents/?latest=1'

        response = requests.get(url)
        kamper = response.json()

        for kamp in kamper:
            kampnavn = kamp.get('match').get('name')
            kommentar = kamp.get('comment')
            if search.lower() in kampnavn.lower():
                resultat = kamp.get('match').get('result')
                hjemme = resultat.get('homeScore90')
                borte = resultat.get('awayScore90')
                if kommentar is None:
                    irc.reply(f'{kampnavn} {hjemme} - {borte}')
                else:
                    irc.reply(f'{kampnavn} {hjemme} - {borte} - {kommentar}')
                break

Class = Fotball


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
