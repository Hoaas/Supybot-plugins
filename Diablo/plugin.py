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
import urllib2
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Diablo')

@internationalizeDocstring
class Diablo(callbacks.Plugin):
    """Fetches Diablo III server status from http://eu.battle.net/d3/en/status
    Defaults to 'eu'."""
    threaded = True
    
    def status(self, irc, msg, args, server):
        """[eu|am|as]
        Diablo status from http://eu.battle.net/d3/en/status
        Defaults to 'eu'."
        """

        if not server:
            server = "eu" # Change this if you do not want the command to
                          # default to 'eu'

        url = "http://eu.battle.net/d3/en/status"
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            html = f.read()
        except:
            irc.reply("Failed to open " + url)
            return
        if server == "am":
            needle = '<div class="column column-1">'
        elif server == "eu":
            needle = '<div class="column column-2">'
        elif server == "as":
            needle = '<div class="column column-3">'
        else:
            irc.reply("Valid arguments are eu (Europe), am (Americas) and as (Asia)")
            return
        
        html = html[ html.find(needle) + len(needle) : ]
        needle = '<h3 class="category">'
        area = html[ html.find(needle) + len(needle) : html.find('</h3>') ]
        
        needle = 'data-tooltip="'
        status = html[ html.find(needle) + len(needle) : html.find('">', html.find(needle) + len(needle)) ]
        
        needle = "Auction House"
        html = html[ html.find(needle) : ]

        needle = 'data-tooltip="'
        gold = html[ html.find(needle) + len(needle) : html.find('">', html.find(needle) + len(needle)) ]

        # Gold happen to stand below the status, so at this point we are done
        # with "Gold".
        needle = "Gold"
        html = html[ html.find(needle) : ]

        needle = 'data-tooltip="'
        hardcore = html[ html.find(needle) + len(needle) : html.find('">', html.find(needle) + len(needle)) ]
        
        if status == "Available":
            status = ircutils.mircColor("↑", "Green")
        else:
            status = ircutils.mircColor(status, "Red")

        if gold == "Available":
            gold = ircutils.mircColor("↑", "Green")
        else:
            gold = ircutils.mircColor(gold, "Red")

        if hardcore == "Available":
            hardcore = ircutils.mircColor("↑", "Green")
        else:
            hardcore = ircutils.mircColor(hardcore, "Red")

        irc.reply("Diablo III server ({0}): {1}. Auction House: Gold {2}. Hardcore {3}.".format(area, status, gold, hardcore))
    status = wrap(status, [optional('text')])

Class = Diablo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
