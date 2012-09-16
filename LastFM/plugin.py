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
import os

#libraries for time_created_at
import time
from datetime import tzinfo, datetime, timedelta

from lxml import etree
import urllib2, urllib

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class LastFM(callbacks.Plugin):
    """Simply returns current playing track for a LastFM user. If no track is
    currently playing the last played track will be displayed."""
    threaded = True
    
    def lastfm(self, irc, msg, args, user):
        """<user>

        Returns last played track for user. If no username is supplies, the
        nick of the one calling the command will be attempted."""
        
        if not user:
            user = msg.nick
        try:
            keyfilepath = os.path.join( os.path.dirname(__file__), 'apikey.txt')
            keyfile = open(keyfilepath, 'r')
            apikey = keyfile.readline()
        except IOError as err:
            irc.reply("Could not open file with apikey. Is it present?")
            self.log.warning("LastFM error, API key missing. Check out README.txt. API key available from http://www.last.fm/api Error message: " + str(err))
            return
        url = "http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks"
        url += "&user=" + urllib.quote(user)
        url += "&limit=1"
        url += "&api_key=" + apikey
        ref = 'irc://%s/%s' % (dynamic.irc.server, dynamic.irc.nick)
        
        charset = "utf-8"

        try:
            # url.encode('iso-8859-1')
            req = urllib2.Request(url)
            req.add_header('Supybot plugin (IRC-bot) (plugin not made public yet)', 'http://sourceforge.net/projects/supybot/')
            req.add_header('Server / nick', ref)
            f = urllib2.urlopen(req)
            xml = f.read()
            #info = f.info()
            #ignore, charset = info['Content-Type'].split('charset=')  
        except urllib2.HTTPError as err:
            if err.code == 403:
                irc.reply(str(err) + " API key not valid?")
            elif err.code == 400:
                irc.reply("No such user.")
            else:
                irc.reply("Could not open URL. " + str(err))
            self.log.debug("Failed to open " + url + " " + str(err))
            return
        except urllib2.URLError as err:
            irc.reply("Error accessing API. It might be down. Please try again later.")
            return
        except:
            raise

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
            irc.reply("Did not find any recent tracks for that user.")
            return
        for attr in recent.items():
            if attr[0] == "user":
                user = attr[1]
        
        track = recent.find("track")
            
        now = False
        if track.items():
            for attr in track.items():
                if attr[0] == "nowplaying" and attr[1] == "true":
                    now = True
        if not now:
            when = track.findtext("date")
            when = self._time_created_at(when) # Remove this line to output
                                               # date in UTC instead.

        artist = track.findtext("artist")
        name = track.findtext("name")
        if not artist or not name or not user:
            irc.reply("Did not find artist, name or username.")
            return
        if now:
            reply = "%s np. %s - %s" % (user, artist, name)
        else:
            reply = "%s last played %s - %s (%s)" % (user, artist, name, ircutils.bold(when))
        irc.reply(reply.encode('utf-8'))

    lastfm = wrap(lastfm, [optional('text')])



    def _time_created_at(self, s):
        """
        recieving text element of 'created_at' in the response of LastFM API,
        returns relative time string from now.
        """

        plural = lambda n: n > 1 and "s" or ""

        # LastFM returns dates in this format: 12 Aug 2012, 17:09
        # and it is in GMT
        try:
            ddate = time.strptime(s, "%d %b %Y, %H:%M")[:-2]
        except ValueError:
            return "", ""

        created_at = datetime(*ddate, tzinfo=None)
        d = datetime.utcnow() - created_at

        if d.days:
            rel_time = "%s days ago" % d.days
        elif d.seconds > 3600:
            hours = d.seconds / 3600
            rel_time = "%s hour%s ago" % (hours, plural(hours))
        elif 60 <= d.seconds < 3600:
            minutes = d.seconds / 60
            rel_time = "%s minute%s ago" % (minutes, plural(minutes))
        elif 30 < d.seconds < 60:
            rel_time = "less than a minute ago"
        else:
            rel_time = "less than %s second%s ago" % (d.seconds, plural(d.seconds))
        return  rel_time

Class = LastFM


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
