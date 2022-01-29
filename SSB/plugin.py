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

import json

import re
import urllib.request, urllib.parse, urllib.error, urllib.request, urllib.error, urllib.parse
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('SSB')

@internationalizeDocstring
class SSB(callbacks.Plugin):
    """Add the help for "@plugin help SSB" here
    This should describe *how* to use this plugin."""
    threaded = True

    def navn(self, irc, msg, args, name):
        """<navn>
        Returnerer info om navnet."""
        url = 'https://www.ssb.no/_/service/mimir/nameSearch?name='
        url += urllib.parse.quote(name)

        data = utils.web.getUrl(url).decode()

        data = json.loads(data)

        docs = data.get('response').get('docs')

        text = ''
        for d in docs:
            text += '{0} ({1} {2})'.format(d.get("count"), d.get("gender"), d.get("type"))
            text += ', '

        text = text[:-2]
        irc.reply(text)
    navn = wrap(navn, ['text'])

Class = SSB


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
