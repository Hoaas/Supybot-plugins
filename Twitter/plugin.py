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
import string
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

#libraries for time_created_at
import time
from datetime import tzinfo, datetime, timedelta

# for unescape
import re, htmlentitydefs


class Twitter(callbacks.Plugin):
    """Simply use the commands available in this plugin. Allows fetching of the
    latest tween from a specified twitter handle, and listing of top ten
    trending tweets."""
    threaded = True

    def _unescape(self, text):
        def fixup(m):
            text = m.group(0)
            if text[:2] == "&#":
                # character reference
                try:
                    if text[:3] == "&#x":
                        return unichr(int(text[3:-1], 16))
                    else:
                        return unichr(int(text[2:-1]))
                except (ValueError, OverflowError):
                    pass
            else:
                # named entity
                try:
                    text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
                except KeyError:
                    pass
            return text # leave as is
        return re.sub("&#?\w+;", fixup, text)
  
    def _time_created_at(self, s):
        """
        recieving text element of 'created_at' in the response of Twitter API,
        returns relative time string from now.
        """

        plural = lambda n: n > 1 and "s" or ""

        try:
            ddate = time.strptime(s, "%a %b %d %H:%M:%S +0000 %Y")[:-2]
        except ValueError:
            return "", ""
        #created_at = datetime(*ddate, tzinfo=None) - timedelta(hours=5)
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

    def trends(self, irc, msg, args):
        """
        Returns the Top 10 Twitter trends world wide..
        """

        #woeid = 23424977 # US
        woeid = 1 # World wide
        try:
            req = urllib2.Request('https://api.twitter.com/1/trends/%s.json' % woeid)
            stream = urllib2.urlopen(req)
            datas = stream.read()
        except urllib2.HTTPError, err:
            if err.code == 404:
                irc.reply("No trend found for given location.")
                self.log.warning("Twitter trends: Failed to find location with WOEID %s." % woeid)
            else:
                self.log.warning("Twitter trends: API returned http error %s" % err.code)
            return
        
        try:
            data = json.loads(datas)
        except:
            irc.reply("Error: Failed to parsed receive data.")
            self.log.warning("Here are data:")
            self.log.warning(data)
            return

        ttrends = string.join([trend['name'] for trend in data[0]['trends']], " | ")
        asof = data[0]['as_of']
        retvalue = ircutils.bold("Current Top 10 Twitter trends: ") + ttrends
        irc.reply(retvalue)

    def twitter(self, irc, msg, args, options, nick):
        """[--reply] [--rt] <nick> | <--id id>

        Returns last tweet (which is not an @reply) by <nick> or tweet with id
        'id'.
        If --reply is given the last tweet will be replied regardless of if it was an @reply or not.
        If --reply is not given, and there are only replies available, the last
        one will be outputed anyway. Same
        Same goes for --rt and retweets.
        """
        id, rt, reply = False, False, False
        if options:
            for (type, arg) in options:
                if type == 'id':
                    id = True
                if type == 'rt':
                    rt = True
                if type == 'reply':
                    reply = True
        if id:
            url = "http://api.twitter.com/1/statuses/show/%s.json" % nick
        else:
            url = "http://api.twitter.com/1/statuses/user_timeline/%s.json" % nick
        if rt and not id:
            url += "?include_rts=true"

        try:
            req = urllib2.Request(url)
            stream = urllib2.urlopen(req)
            datas = stream.read()
        except urllib2.URLError, (err):
            if (err.code and err.code == 404):
                irc.reply("User or tweet not found.")
            elif (err.code and err.code == 401):
                irc.reply("Not authorized. Protected tweets?")
            else:
                if (err.code):
                    irc.reply("Error: Looks like I haven't bothered adding a special case for http error #" + str(err.code))
                else:
                    irc.reply("Error: Failed to open url. API might be unavailable.")
            return
        try:
            data = json.loads(datas)
        except:
            irc.reply("Error: Failed to parsed receive data.")
            self.log.warning("Plugin Twitter failed to parse json-data. Here are the data:")
            self.log.warning(data)
            return

        # If an ID was given.
        if id:
            text = self._unescape(data["text"]).encode("utf-8")
            nick = data["user"]["screen_name"].encode("utf-8")
            name = data["user"]["name"].encode("utf-8")
            date = data["created_at"]
            relativeTime = self._time_created_at(date)
            irc.reply("{0} ({1}): ({2})".format(name, ircutils.underline(ircutils.bold("@" + nick)), self._unescape(text), ircutils.bold(relativeTime)))
            return

        # If it was a regular nick
        if len(data) == 0:
            irc.reply("User has not tweeted yet.")
            return
        # Loop over all tweets
        for i in range(len(data)):
            # If we don't want @replies
            if (not reply and not data[i]["in_reply_to_screen_name"]):
                index = i
                break
            # If we want the last tweet even if it is an @reply
            elif (reply):
                index = i
                break
            # In order to avoid error if we don't want replies, but there is
            # nothing else.
            else:
                index = 0
        name = data[index]["user"]["name"].encode('utf-8')
        nick = data[index]["user"]["screen_name"].encode('utf-8')
        text = data[index]["text"].encode('utf-8')
        date = data[index]["created_at"]

        relativeTime = self._time_created_at(date)

        irc.reply("{0} ({1}): ({2})".format(name, ircutils.underline(ircutils.bold("@" + nick)), self._unescape(text), ircutils.bold(relativeTime)))
#        [getopts({'current': '', 'forecast': '', 'all': ''})
    twitter = wrap(twitter, [getopts({'reply':'', 'rt': '', 'id': ''}), ('something')])


Class = Twitter


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
