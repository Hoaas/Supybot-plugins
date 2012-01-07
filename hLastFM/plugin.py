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
from lxml import etree
import urllib2, urllib

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class hLastFM(callbacks.Plugin):
    """Add the help for "@plugin help hLastFM" here
    This should describe *how* to use this plugin."""
    threaded = True
    
    def lastfm(self, irc, msg, args, user):
        """<user>

        Returns last played track for user"""
        
        if not user:
            user = msg.nick
        url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks"
        url += "&user=" + user
        url += "&limit=1"
        url += "&api_key=your-api-key-here"
        ref = 'irc://%s/%s' % (dynamic.irc.server, dynamic.irc.nick)
        
        charset = "utf-8"
        
        try:
            # url.encode('iso-8859-1')
            req = urllib2.Request(url)
            req.add_header('Supybot plugin (IRC-bot) (plugin not made public yet)', 'http://sourceforge.net/projects/supybot/')
            req.add_header('Server / nick', ref)
            f = urllib2.urlopen(req)
            xml = f.read()
            info = f.info()
            ignore, charset = info['Content-Type'].split('charset=')  
        except:
            print "Failed to open " + url
            irc.reply("Did not find any tracks for that user. (actually, HTTPError.)")
            return
        try:
            root = etree.fromstring(xml)
        except:
            irc.reply("There appear to be some problems parsing the XML data.")
            return
        
        
        for attr in root.items():
            if attr[0] == "status" and attr[1] == "failed":
                irc.reply(status.findtext("error"))
        
        # Find element
        recent = root.find("recenttracks")
        if len(recent) == 0:
            irc.reply("Did not find any recent tracks for that user. (e001)")
            return
        if not recent.items():
            irc.reply("Did not find any recent tracks for that user. (e002)")
            return
        for attr in recent.items():
            if attr[0] == "user":
                user = attr[1]
        
        track = recent.find("track")
        if len(track) == 0:
            irc.reply("Did not find any recent tracks for that user. (e003)")
            
        now = False
        if track.items():
            for attr in track.items():
                if attr[0] == "nowplaying" and attr[1] == "true":
                    now = True
        if not now:
            when = track.findtext("date")
        
        artist = track.findtext("artist")
        name = track.findtext("name")
        if not artist or not name or not user:
            irc.reply("Did not find artist, name or username.")
            return
        if now:
            reply = user + " np. " + artist + " - " + name
        else:
            reply = user + " last played " + artist + " - " + name + " (" + when + ")"
        irc.reply(reply.encode('utf-8'))

    lastfm = wrap(lastfm, [optional('text')])

Class = hLastFM


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
