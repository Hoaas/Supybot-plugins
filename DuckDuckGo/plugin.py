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
        if duckduckgo.__version__ < 0.2:
            self.log.error('DuckDuckGo requires python-duckduckgo2 > 0.2')

    def ddg(self, irc, msg, args, query):
        """<query>

        Searches duckduckgo.com and returns any zero-click information or a web
        result, if any."""
        
        showurl = self.registryValue('showURL')
        safesearch = self.registryValue('safeSearch')
        maxreplies = self.registryValue('maxReplies')
        weblink = self.registryValue('webLink')
        PRIORITY = ['answer', 'abstract', 'related.0', 'definition', 'related']
        showaddionalhits = False
        
        repliessofar = 0
        
        res = duckduckgo.query(
                query,
                safesearch=safesearch,
                useragent='Supybot plugin (IRC-bot) https://github.com/Hoaas/Supybot-plugins/tree/master/DuckDuckGo'
        )

        
        response = []

        for p in PRIORITY:
            ps = p.split('.')
            ptype = ps[0]
            index = int(ps[1]) if len(ps) > 1 else None

            result = getattr(res, ptype)
            if index is not None and len(result) >= index+1: result = result[index]

            if type(result) != list: result = [result]

            for r in result:
                if len(response) >= maxreplies: break
                rline = ''
                if r.text: rline = r.text
                if r.text and hasattr(r,'url') and showurl: 
                    if r.url: rline += ' (%s)' % r.url
                if rline: response.append(rline)

            if response: break

        # if there still isn't anything, try to get the first web result
        if not response and weblink:
            ddgr = duckduckgo.query(
                    '! '+query,
                    safesearch=safesearch,
                    useragent='Supybot plugin (IRC-bot) https://github.com/Hoaas/Supybot-plugins/tree/master/DuckDuckGo'
            ).redirect.url
            if ddgr:
                response = [ddgr]

        # final fallback
        if not response: 
            response = ['Sorry, no results.']

        for resp in response:
            irc.reply(unicode(resp).encode('utf-8'))
              
    ddg = wrap(ddg, ['text'])
        

Class = DuckDuckGo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
