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

import urllib2
import json
import datetime
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Twitter(callbacks.Plugin):
    """Add the help for "@plugin help Twitter" here
    This should describe *how* to use this plugin."""
    threaded = True

    def twitter(self, irc, msg, args, nick):
        """<nick>

        Returns last tweet by <nick>.
        """
        url = "http://api.twitter.com/1/users/lookup.json?screen_name=" + nick
        try:
            req = urllib2.Request(url)
            stream = urllib2.urlopen(req)
            data = stream.read()
        except urllib2.URLError, (err):
            if(err.code and err.code == 404):
                irc.reply("User not found.")
            else:
                irc.reply("Error: Failed to open url. API might be unavailable.")
            return
        try:
            data = json.loads(data)
        except:
            irc.reply("Error: Failed to parsed receive data.")
            return
#        print "--------- This is the full json ---------"
#        print json.dumps(data, sort_keys=True, indent=4)
#        print "--------- That was it! ---------"
        if (len(data) != 1):
            retvalue = "No data from API. -> " + url
        elif(data[0]["protected"]):
            retvalue = "Protected feed."
        else:
            try:
                name = data[0]["screen_name"]
                text = data[0]["status"]["text"]
                date = data[0]["status"]["created_at"]
                retvalue = "Tweeted by " + name + ", " + date + ": " + text
            except KeyError, (err):
                retvalue = "User has not tweeted yet, or no tweet available at " + url

#        date_object = datetime.strptime(date,  "%a %b %d %H:%M:%S +0000 %Y")

        irc.reply(retvalue.encode("utf-8"))
    twitter = wrap(twitter, ['text'])


Class = Twitter


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
