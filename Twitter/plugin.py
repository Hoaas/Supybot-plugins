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
        text = text.replace("\n", " ")
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

        # twitter search and timelines use different timeformats
        # timeline's created_at Tue May 08 10:58:49 +0000 2012
        # search's created_at Thu, 06 Oct 2011 19:41:12 +0000

        try:
            ddate = time.strptime(s, "%a %b %d %H:%M:%S +0000 %Y")[:-2]
        except ValueError:
            try:
                ddate = time.strptime(s, "%a, %d %b %Y %H:%M:%S +0000")[:-2]
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

    def trends(self, irc, msg, args):
        """
        Returns the Top 10 Twitter trends world wide..
        """

        woeid = self.registryValue('woeid', msg.args[0]) # Where On Earth ID
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
        # asof = data[0]['as_of'] #asof date if you want to use
        retvalue = ircutils.bold("Current Top 10 Twitter trends: ") + ttrends
        irc.reply(retvalue)


    def tsearch(self, irc, msg, args, optlist, term):
        """ [--num number] [--searchtype mixed | recent | popular] [--lang xx] <term>

        Searches Twitter for the <term> and returns the most recent results.
        Number is number of results. Must be a number higher than 0 and max 10.
        searchtype being recent, popular or mixed. Popular is the default.
        """

        url = "http://search.twitter.com/search.json?include_entities=false&q=" + urllib.quote(term)
        # https://dev.twitter.com/docs/api/1/get/search
        # https://dev.twitter.com/docs/using-search

        num, searchtype, lang = False, False, False

        if optlist:
            for (type, arg) in optlist:
                if type == 'num':
                    num = arg
                if type == 'searchtype':
                    searchtype = arg
                if type == 'lang':
                    lang = arg
        url += "&rpp="
        if not num:
            num = 3
        url += str(num)

        # mixed: Include both popular and real time results in the response.
        # recent: return only the most recent results in the response
        # popular: return only the most popular results in the response.
        if searchtype:
            url += "&result_type=" + searchtype
        
        # lang . Uses ISO-639 codes like 'en'
        # http://en.wikipedia.org/wiki/ISO_639-1
        if lang:
            url += "&lang=" + lang

        self.log.info(url)
        try:
            req = urllib2.Request(url)
            stream = urllib2.urlopen(req)
            datas = stream.read()
        except urllib2.URLError, (err):
            if (err.code and err.code == 406):
                irc.reply("Invalid format is specified in the request.")
            elif (err.code and err.code == 420):
                irc.reply("You are being rate-limited by the Twitter API.")
            else:
                if (err.code):
                    irc.reply("Missing error" + str(err.code))
                else:
                    irc.reply("Error: Failed to open url.")
            return
        try:
            data = json.loads(datas)
        except:
            irc.reply("Error: Failed to parsed receive data.")
            self.log.warning("Plugin Twitter failed to parse json-data.")
            self.log.warning(data)
            return

        results = data["results"]
        outputs = 0
        if len(results) == 0:
            irc.reply("Error: No Twitter Search results found: %s" % term)
        else:
            for result in results:
                if outputs >= num:
                    return
                nick = result["from_user"].encode('utf-8')
                name = result["from_user_name"].encode('utf-8')
                text = self._unescape(result["text"]).encode('utf-8')
                date = result["created_at"]
                relativeTime = self._time_created_at(date)
                tweetid = result["id"]
                self._outputTweet(irc, msg, nick, name, text, relativeTime, tweetid)
                outputs += 1

    tsearch = wrap(tsearch, [getopts({'num':('int', 'number of results', lambda i: 0 < i <= 10), 'searchtype':('literal', ('popular', 'mixed', 'recent')), 'lang':('something')}), ('text')])

    def _outputTweet(self, irc, msg, nick, name, text, time, tweetid):
        ret = ircutils.underline(ircutils.bold("@" + nick))
        hideName = self.registryValue('hideRealName', msg.args[0])
        if not hideName:
            ret += " ({})".format(name)
        ret += ": {0} ({1})".format(text, ircutils.bold(time))
        if self.registryValue('addShortUrl', msg.args[0]):
            url = self._createShortUrl(nick, tweetid)
            if (url):
                ret += " {0}".format(url)
        irc.reply(ret)

    def _createShortUrl(self, nick, tweetid):
        longurl = "https://twitter.com/#!/{0}/status/{1}".format(nick, tweetid)
        try:
            req = urllib2.Request("http://is.gd/api.php?longurl=" + urllib.quote(longurl))
            f = urllib2.urlopen(req)
            shorturl = f.read()
            return shorturl
        except:
            return False

    def twitter(self, irc, msg, args, options, nick):
        """[--reply] [--rt] [--num number] <nick> | <--id id> | [--info nick]

        Returns last tweet or 'number' tweets (max 10). Only replies tweets that are
        @replies or retweets if specified with the appropriate arguments.
        Or returns tweet with id 'id'.
        Or returns information on user with --info. 
        """
        id, rt, reply, num, info = False, False, False, False, False
        if options:
            for (type, arg) in options:
                if type == 'id':
                    id = True
                if type == 'rt':
                    rt = True
                if type == 'reply':
                    reply = True
                if type == 'num':
                    num = arg
                if type == 'info':
                    info = True
        if not num:
            num = 1

        if id:
            url = "http://api.twitter.com/1/statuses/show/%s.json" % urllib.quote(nick)
        elif info:
            url = "https://api.twitter.com/1/users/show.json?screen_name=%s" % urllib.quote(nick)
        else:
            url = "http://api.twitter.com/1/statuses/user_timeline/%s.json" % urllib.quote(nick)
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
            text = self._unescape(data["text"]).encode('utf-8')
            nick = data["user"]["screen_name"].encode('utf-8')
            name = data["user"]["name"].encode('utf-8')
            date = data["created_at"]
            relativeTime = self._time_created_at(date)
            tweetid = data["id"]
            self._outputTweet(irc, msg, nick, name, text, relativeTime, tweetid)
            return

        # If info was given
        if info:
            location = data['location'].encode('utf-8')
            followers = data['followers_count']
            friends = data['friends_count']
            description = data['description'].encode('utf-8')
            screen_name = data['screen_name'].encode('utf-8')
            name = data['name'].encode('utf-8')
            url = data['url']
            if url:
                url = url.encode('utf-8')
    
            ret = ircutils.underline(ircutils.bold("@" + nick))
            ret += " ({}):".format(name)
            if url:
                ret += " {}".format(ircutils.underline(url))
            if description:
                ret += " {}".format(description)
            ret += " {} friends,".format(ircutils.bold(friends))
            ret += " {} followers.".format(ircutils.bold(followers))
            if location: 
                ret += " " + location
            #irc.reply("%s %s %s %s %s %s %s" % (screen_name, name, url, description, friends, followers, location))
            ret = ret.replace("\r", "")
            ret = ret.replace("\n", " ")
            irc.reply(ret)
            return

        # If it was a regular nick
        if len(data) == 0:
            irc.reply("User has not tweeted yet.")
            return
        indexlist = []
        counter = 0
        # Loop over all tweets
        for i in range(len(data)):
            if counter >= num:
                break
            # If we don't want @replies
            if (not reply and not data[i]["in_reply_to_screen_name"]):
                indexlist.append(i)
                counter += 1
            # If we want this tweet even if it is an @reply
            elif (reply):
                indexlist.append(i)
                counter += 1

        for index in indexlist:
            text = self._unescape(data[index]["text"]).encode('utf-8')
            nick = data[index]["user"]["screen_name"].encode('utf-8')
            name = data[index]["user"]["name"].encode('utf-8')
            date = data[index]["created_at"]
            tweetid = data[index]["id"]
            relativeTime = self._time_created_at(date)

            self._outputTweet(irc, msg, nick, name, text, relativeTime, tweetid)

        # If more tweets were requested than were found
        if len(indexlist) < num:
            irc.reply("You requested {} tweets but there were {} that matched your requirements.".format(num, len(indexlist)))
    twitter = wrap(twitter, [getopts({'reply':'', 'rt': '', 'info': '', 'id': '', 'num': ('int', 'number of tweets', lambda i: 0 < i <= 10)}), ('something')])


    def tagdef(self, irc, msg, args, term):
        """<term>
        Returns the tag defition from tagdef.com
        """

        # tagdef API: http://api.tagdef.com/
        # tagdef seems to break when you ask and issue
        # #hashtag when you need to submit hashtag
        term = term.replace('#','')

        try:
            req = urllib2.Request('http://api.tagdef.com/one.%s.json' % term)
            stream = urllib2.urlopen(req)
            datas = stream.read()
        except urllib2.HTTPError, err:
            if err.code == 404:
                irc.reply("No tag definition found for: %s" % term)
                self.log.warning("Failed to find definition for %s." % term)
            else:
                self.log.warning("tagdef API returned error %s" % err.code)
            return

        try:
            data = json.loads(datas)
        except:
            irc.reply("Error: Failed to parse received data.")
            self.log.warning("Failed to parse tagdef data.")
            self.log.warning(datas)
            return

        number_of = data['num_defs'] # number of definitions
        definition = data['defs']['def']['text']
        # time = data['defs']['def']['time']
        # upvotes = data['defs']['def']['upvotes']
        # downvotes = data['defs']['def']['downvotes']
        uri = data['defs']['def']['uri']

        retvalue = ircutils.underline("Tagdef: #%s" % term) + " " + definition + " " + uri
        irc.reply(retvalue)
    tagdef = wrap(tagdef, ['text'])

Class = Twitter


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=279:
