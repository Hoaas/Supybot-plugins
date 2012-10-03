# coding=utf8
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
import duckduckgo
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class DuckDuckGo(callbacks.Plugin):
    """This addon uses the search engine DuckDuckGo's (@ duckduckgo.com) Zero-Click info.
    It extract info from a long range of sources, like wikipedia, IMDB and so forth.
    One example is simply searching for "h2o" will give you information about water. 
    See duckduckgo.com for more information."""
    threaded = True
    def __init__(self, *args, **kwargs):
        super(DuckDuckGo, self).__init__(*args, **kwargs)
        if duckduckgo.__version__ < 0.24:
            self.log.error('DuckDuckGo requires python-duckduckgo2 >= 0.24')

    def ddg(self, irc, msg, args, options, query):
        """[--answer | --abstract | --related | --define] <query>

        Searches duckduckgo.com and returns any zero-click information or a web
        result, if any. Using options overrides normal priority."""
        
        showurl = self.registryValue('showURL')
        safesearch = self.registryValue('safeSearch')
        maxreplies = self.registryValue('maxReplies')
        weblink = self.registryValue('webLink')
        showaddionalhits = False
        
        PRIORITY = ['answer', 'abstract', 'related.0', 'definition', 'related']
        
        if options:
            weblink = False
            for (key, value) in options:
                if key == 'answer':
                    PRIORITY = ['answer']
                    break
                if key == 'abstract':
                    PRIORITY = ['abstract']
                    break
                if key == 'related':
                    PRIORITY = ['related.0']
                    break
                if key == 'define':
                    PRIORITY = ['definition']
                    break

        res = duckduckgo.get_zci(
                query,
                web_fallback=weblink,
                safesearch=safesearch,
                priority=PRIORITY,
                urls=showurl,
                useragent='Supybot plugin (IRC-bot) https://github.com/Hoaas/Supybot-plugins/tree/master/DuckDuckGo'
        )
        irc.reply(res)
    ddg = wrap(ddg, [getopts({'answer':'', 'abstract':'','related':'', 'define':''}), 'text'])

Class = DuckDuckGo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
