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

    def rt(self, irc, msg, args, movie):
        """<movie>
        
        Returns info about a movie from Rotten Tomatoes."""
        apikey = self.registryValue('apikey')
        if not apikey or apikey == "Not set":
            irc.reply("API key not set. see 'config help supybot.plugins.RottenTomatoes.apikey'.")
            return

        url = "http://api.rottentomatoes.com/api/public/v1.0/movies.json?apikey="
        url += urllib.quote(apikey)
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
        #self.log.info(json.dumps(j, sort_keys=True, indent=4))
        try:
            movie = j["movies"][0]
        except:
            irc.reply("No movie found by that name :(")
            return
        title = movie["title"]
        try:
            consensus = movie["critics_consensus"]
        except:
            consensus = None

        ratings = movie["ratings"]
        critics_score = str(ratings["critics_score"]) + "%"
        critics_rating = ratings["critics_rating"]
        audience_score = str(ratings["audience_score"]) + "%"
        audience_rating = ratings["audience_rating"]

        if critics_rating == "Certified Fresh" or critics_rating == "Fresh":
            critics_score = ircutils.mircColor(critics_score, "Red")
        elif critics_rating == "Rotten":
            critics_score = ircutils.mircColor(critics_score, "Green")
        if audience_rating == "Upright":
            audience_score = ircutils.mircColor(audience_score, "Red")
        elif audience_rating == "Spilled":
            audience_score = ircutils.mircColor(audience_score, "Green")

        if consensus:
            irc.reply("{0} - Critics: {1}. Audience: {2}. {3}".format(ircutils.bold(title), critics_score, audience_score, consensus))
        else:
            irc.reply("{0} - Critics: {1}. Audience: {2}.".format(ircutils.bold(title), critics_score, audience_score))


    rt = wrap(rt, ['text'])

Class = RottenTomatoes


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
