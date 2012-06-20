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

import json
import urllib, urllib2

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('RottenTomatoes')

@internationalizeDocstring
class RottenTomatoes(callbacks.Plugin):
    """Add the help for "@plugin help RottenTomatoes" here
    This should describe *how* to use this plugin."""
    threaded = True

    def rt(self, irc, msg, args, pageid, movie):
        """[id] <movie>
        
        Returns info about a movie from Rotten Tomatoes. Id is a positive
        integer and can be used in case there are several hits."""
        apikey = self.registryValue('apikey')
        if not apikey or apikey == "Not set":
            irc.reply("API key not set. see 'config help supybot.plugins.RottenTomatoes.apikey'.")
            return
        if not pageid:
            pageid = 1
        url = "http://api.rottentomatoes.com/api/public/v1.0/movies.json?apikey="
        url += urllib.quote(apikey)
        url += "&page_limit=1&page=" + str(pageid)
        url += "&q=" + urllib.quote(movie)

        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            jsonstr = f.read()
        except urllib2.HTTPError as err:
            if err.code == 404:
                irc.reply("404 etc.")
            elif err.code == 403:
                irc.reply("Not Authorized. Wrong API key? Check 'config help supybot.plugins.RottenTomatoes.apikey'.")
            irc.reply(err.code)
            return

        try:
            j = json.loads(jsonstr)
        except:
            irc.reply("Failed to load JSON from Rotten Tomatoes API.")
            return
        self._returnRatings(irc, j)
    rt = wrap(rt, [optional('positiveInt'), 'text'])
    
    def _returnRatings(self, irc, json):
        try:
            movie = json["movies"][0]
        except:
            irc.reply("No movie found by that name :(")
            return
        out = ""
        try:
            title = movie["title"]
            out += ircutils.bold(title)
        except:
            irc.reply("This movie has no title. :s")
            return

        try:
            year = movie["year"]
            out += " ({0}) - ".format(year)
        except:
            pass
      

        try:
            ratings = movie["ratings"]
        except:
            ratings = None

        if ratings:
            try:
                critics_score = ratings["critics_score"]
                if critics_score < 0:
                    critics_score = None
                else:
                    critics_score = str(critics_score) + "%"
            except:
                critics_score = None
            try:
                critics_rating = ratings["critics_rating"]
            except:
                critics_rating = None
    
            try:
                audience_score = ratings["audience_score"]
                if audience_score < 0:
                    audience_score = None
                else:
                    audience_score = str(audience_score) + "%"
            except:
                audience_score = None
            try:
                audience_rating = ratings["audience_rating"]
            except:
                audience_rating = None

            if critics_score:
                if critics_rating and (critics_rating == "Certified Fresh" or
                        critics_rating == "Fresh"):
                    critics_score = ircutils.mircColor(critics_score, "Red")
                elif critics_rating and (critics_rating == "Rotten"):
                    critics_score = ircutils.mircColor(critics_score, "Green")
                else:
                    critics_score = ircutils.bold(critics_score)
                out += "{0}: {1}".format(ircutils.bold("Critics"), critics_score)
                if critics_rating:
                    out += " ({0}). ".format(critics_rating)
                else:
                    out += ". "

            if audience_score:
                if audience_rating and audience_rating == "Upright":
                    audience_score = ircutils.mircColor(audience_score, "Red")
                elif audience_rating and audience_rating == "Spilled":
                    audience_score = ircutils.mircColor(audience_score, "Green")
                else:
                    audience_score = ircutils.bold(audience_score)
                out += "{0}: {1}".format(ircutils.bold("Audience"), audience_score)
                if audience_rating:
                    out += " ({0}). ".format(audience_rating)
                else:
                    out += ". "

        try:
            consensus = movie["critics_consensus"]
            out += consensus + " "
        except:
            pass

        try:
            total = json["total"]
            if(total > 1):
                out += "Total of {0} movies found.".format(ircutils.bold(total))
        except:
            pass

        irc.reply(out)

Class = RottenTomatoes


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
