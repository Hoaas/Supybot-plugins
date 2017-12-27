###
# Copyright (c) 2016, Terje Hoås
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
import urllib

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('OMDb')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x


class OMDb(callbacks.Plugin):
    """Information about movies (and maybe series?) from omdbapi.com, which, at the time of writing, can get info from Metacritic, Rotten Tomatoes and IMDb."""
    threaded = True

    url = "http://www.omdbapi.com/?"

    @wrap([getopts({'year':'int'}),'text'])
    def omdb(self, irc, msg, args, opts, movie):
        """[--year <int>] <movie>
        Shows some information about the given movie title.
        """

        apikey = self.registryValue('apikey')
        if not apikey or apikey == "Not set":
            irc.reply("API key not set. See 'config help supybot.plugins.OMDb.apikey'.")
            return

        url = self.url
        url += "apikey=" + apikey
        url += "&t=" + urllib.parse.quote(movie)
        url += "&plot=short"
        url += "&tomatoes=true"
        url += "&r=json"

        if opts:
            opts = dict(opts)
            year = opts.get('year')
            if year:
                url += "&y=" + str(year)

        jsonstr = utils.web.getUrl(url).decode()
        j = json.loads(jsonstr)
        error = j.get("Error")
        if error:
            irc.reply(error)
            return
        retval = "[{0}] ({1}) {2} Metacritic: [{3}] RT: [{4} / {5}] IMDb: [{6}] Actors: [{7}] {8}".format(
                ircutils.bold(j.get("Title")),
                j.get("Year"),
                j.get("Genre"),
                self.metacolor(j.get("Metascore")),
                self.rtcolor(j.get("tomatoMeter")),
                self.rtcolor(j.get("tomatoUserMeter")),
                self.imdbcolor(j.get("imdbRating")),
                j.get("Actors"),
                j.get("Plot")
            )
        irc.reply(retval)
    
    def metacolor(self, score):
        if not score.isdigit():
            return score
        scoreNum = int(score)
        if scoreNum >= 60:
            return ircutils.mircColor(score + "%", "Green")
        if scoreNum >= 40:
            return ircutils.mircColor(score + "%", "Yellow")
        else:
            return ircutils.mircColor(score + "%", "Red")
    
    def imdbcolor(self, score):
        try:
            scoreNum = float(score)
        except:
            return score
        if (scoreNum) >= 8.0:
            return ircutils.mircColor(score, "Green")
        if (scoreNum) >= 6.0:
            return ircutils.mircColor(score, "Yellow")
        if (scoreNum) >= 4.0:
            return ircutils.mircColor(score, "Orange")
        else:
            return ircutils.mircColor(score, "Red")

    def rtcolor(self, score):
        if not score.isdigit():
            return score
        scoreNum = int(score)
        if scoreNum  > 59:
            return ircutils.mircColor(score + "%", "Red")
        else:
            return ircutils.mircColor(score + "%", "Green")
    
Class = OMDb
