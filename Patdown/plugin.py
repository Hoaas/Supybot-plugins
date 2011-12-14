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
import socket
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('Patdown')

@internationalizeDocstring
class Patdown(callbacks.Plugin):
    """Add the help for "@plugin help Patdown" here
    This should describe *how* to use this plugin."""
    threaded = True

    def patdown(self, irc, msg, args, user):   
        """patdown <nick|ip|hostname>
        Checks if the target has any record at http://www.youhavedownloaded.com/
        """
        # If input is an IP
        try:
            socket.inet_aton(user)
            ip = user
            input = None
            user = None

        except socket.error:
            # If it is a nick in the channel
            if ( irc.isNick(user) and user in irc.state.channels[msg.args[0]].users ):
                hostname = irc.state.nickToHostmask(user)
                hostname = hostname[hostname.find("@")+1:]
            # Possibly an hostname?
            else:
                hostname = user
                user = None
            try:
                __, __, ip = socket.gethostbyname_ex(hostname)
            except socket.herror:
                irc.reply("ALERT! ERROR! No srsly, not sure what this is.")
                return
            except socket.gaierror:
                irc.reply("No IP found. (it was a hostname, right?)")
                return
            ip = ip[0]
        
        url = "http://www.youhavedownloaded.com/?q=" + ip
        text = ""
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            text = f.read()
        except:
            irc.reply("Failed to open " + url)
            return
        t = text.find("<title>")
        what = text[t+5:text.find("</title>", t)]
        what = what[what.find("IP")+3:]
        what = what[:what.find(" | ")]

        if ( what == "No results" ):
            irc.reply("Failed to look up ip.")
            return

        d = text.find("Downloaded files")+len("Downloaded files</h3>")
        s = text.find("</table>", d)+8

        if ( text.find("Downloaded files") == -1 ):
            irc.reply(ip + " is clean.")
            return
        text = text[d:s]

        i = text.find("<")
        while ( i != -1 ):
            substr = text[i:text.find(">", i)+1]
            text = text.replace(substr, "")
            i = text.find("<")

        torrents = text.splitlines()
        cleanlist = []
        for l in torrents:
            if l.strip() != "":
                cleanlist.append(l.strip())
        cleanlist = cleanlist[2:]
        ret = ""
        for i in range(len(cleanlist)):
            if (i % 2 == 0):
                ret += cleanlist[i] + ", "
        ret = ret[:-2]
        if user:
            irc.reply(user + " (" + ip + ") has downloaded: " + ret)
        else:
            irc.reply(ip + " has downloaded: " + ret)


    patdown = wrap(patdown, ['text'])

Class = Patdown


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
