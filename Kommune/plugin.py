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

import os
import json

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Kommune')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class Kommune(callbacks.Plugin):
    """List of all counties in Norway as of October 2015"""
    threaded = True

    def kommune(self, irc, msg, args, search):
        """<kommune>
        Info om kommunen."""
        path = os.path.dirname(__file__)
        jsonfile = os.path.join(path, 'kommuner.json')
        with open(jsonfile) as json_file:
            data = json.load(json_file)
        kommuner = data.get('kommuner')
        hit = False
        for kommune in kommuner:
            if kommune.get('Kommune').lower()  == search.lower():
                irc.reply(self.formatedString(kommune))
                hit = True
        if hit:
            return

        for kommune in kommuner:
            if kommune.get('Kommune').lower().startswith(search.lower()):
                irc.reply(self.formatedString(kommune))
                return

        for kommune in kommuner:
            if kommune.get('Kommune').lower().find(search.lower()) != -1:
                irc.reply(self.formatedString(kommune))
                return
        irc.error('NoSuchKommuneException. You suck.')
    kommune = wrap(kommune, ['text'])

    def formatedString(self, kommune):
        ret = '{0} - {1} (Adm. senter {2}) i {3}. {4} innbyggere. {5} km². Målform {6}.'.format(kommune.get('Nr'), kommune.get('Kommune'), kommune.get('Adm. senter'), kommune.get('Fylke'), kommune.get('Folketall'), kommune.get('Areal'), kommune.get('Målform').lower())
        return ret

Class = Kommune
