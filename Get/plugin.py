###
# Copyright (c) 2014, Terje Hoås
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
from html.parser import HTMLParser
import dateutil.parser

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Get')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class Get(callbacks.Plugin):
    """Add the help for "@plugin help Get" here
    This should describe *how* to use this plugin."""
    threaded = True

    url = 'https://www.get.no/portalbackend/api/support/operational-statuses/?zip='

    def get(self, irc, msg, args, postnum):
        """<postnummer>
        Returnerer siste driftsmeldinger om bredbånd for gitt postnummer fra Get.no.
        """
        if len(postnum) != 4 or not postnum.isdigit():
            irc.error("Postnummer må være 4 siffer.")
            return
        url = self.url + postnum
        data = utils.web.getUrl(url).decode('utf8')
        problemlist = json.loads(data)
        count = 0
        for problem in problemlist:
            if problem.get('servicesAffected') is None:
                continue
            if 'bredbånd' not in problem['servicesAffected'] and 'Bredbånd' not in problem['servicesAffected']:
                continue
            count += 1
            message = self.strip_tags(problem['message']).replace('\r', '').replace('\n', ' ') # Remove new lines and html from the text
            message = re.sub(' +', ' ', message) # Remove double spaces
            date = problem['affectedPeriodFrom']
            date = dateutil.parser.parse(date)
            date = date.strftime('%Y-%m-%d %H:%M')
            irc.reply('{1}. {0}. {2}'.format(problem['status'], date, message))
        if count == 0:
            irc.reply('Ingen problemer med bredbånd!')
    get = wrap(get, ['text'])

    def strip_tags(self, html):
        s = MLStripper()
        s.feed(html)
        return s.get_data()
Class = Get


class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.strict = False
        self.convert_charrefs= True
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)
