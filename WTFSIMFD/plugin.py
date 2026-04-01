###
# Copyright (c) 2010, Terje Hoås
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
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('WTFSIMFD')
except ImportError:
    _ = lambda x: x


class WTFSIMFD(callbacks.Plugin):
    """Fetches a random dinner suggestion from WhatTheFuckShouldIMakeForDinner.com."""
    threaded = True

    def dinner(self, irc, msg, args):
        """takes no arguments

        Fetches a random dinner suggestion from WhatTheFuckShouldIMakeForDinner.com.
        """
        url = 'http://www.whatthefuckshouldimakefordinner.com/'
        html = utils.web.getUrl(url).decode(errors='ignore')
        html = html[html.find('<dl>')+4:]
        insult = html[:html.find('</dl>')].strip()

        html = html[html.find('<dl>')+4:]
        html = html[html.find('<a href="')+9:]
        dinnerurl = html[:html.find('"')].strip()

        html = html[html.find('>')+1:]
        dinner = html[:html.find('</a>')].strip()
        irc.reply(f'{insult} {dinner}. ({dinnerurl})')
    dinner = wrap(dinner)

Class = WTFSIMFD
