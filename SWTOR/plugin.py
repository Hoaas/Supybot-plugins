# coding=utf8
###
# Copyright (c) 2011, Terje Hoås
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

import urllib, urllib2
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('SWTOR')

@internationalizeDocstring
class SWTOR(callbacks.Plugin):
    """Add the help for "@plugin help SWTOR" here
    This should describe *how* to use this plugin."""
    threaded = True
    
    def _status(self, html, server):
        location = html.find('data-name="' + server)
        if location == -1:
            return -1, -1, -1, -1, -1
        
        # Assuming this tag always stays the same
        statloc = html.find('<div class="status">', location)
        statloc = html.find('<span class=', statloc)
        statloc = html.find('>', statloc) + 1
        status = html[statloc:html.find('</span>', statloc)]
        
        nameloc = html.find('<div class="name">', location) + len('<div class="name">')
        name = html[nameloc:html.find('<', nameloc)]
        
        loadloc = html.find('<div class="population', location)
        loadloc = html.find('>', loadloc) + 1
        load = html[loadloc:html.find('<', loadloc)]

        typeloc = html.find('<div class="type">', location)
        typeloc = html.find('>', typeloc) + 1
        stype = html[typeloc:html.find('<', typeloc)]

        langloc = html.find('<div class="language">', location)
        langloc = html.find('>', langloc) + 1
        lang = html[langloc:html.find('<', langloc)]
#        return str(statloc), str(nameloc), str(loadloc), str(typeloc), str(langloc)
        return status, name, load, stype, lang
        
        


    def status(self, irc, msg, args, server):
        """status [server]
        Returns the status of the selected server, and general stats about all
        servers.
        """
        if not server:
            server = "Scepter of Ragnos"
        server = server.lower()
        
        url = "http://www.swtor.com/server-status"
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            html = f.read()
        except:
            irc.reply("Failed to open " + url)
            return
        downmessageloc = html.find("SWTOR.com is currently unavailable while we perform scheduled maintenance. Please check back again soon!")
        if downmessageloc != -1:
            irc.reply("SWTOR.com is currently unavailable while we perform scheduled maintenance. Please check back again soon!")
            return
        html = html[html.find('<div id="mainBody">'):html.find('<div class="mainContentFullBottom">')]
        
        status, name, load, stype, lang = self._status(html, server.lower())
        
        if (status == -1):
            irc.reply('Could not find a servername that starts with "' + server
                    + '"')
            return
        irc.reply(name + ": " + status + ". Population load: " + load + ". " + stype + ". " + lang + ".")

    status = wrap(status, [optional('text')])
    

Class = SWTOR


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
