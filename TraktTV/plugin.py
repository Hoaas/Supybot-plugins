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
import datetime
import urllib, urllib2
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('TraktTV')

@internationalizeDocstring
class TraktTV(callbacks.Plugin):
    """Add the help for "@plugin help TraktTV" here
    This should describe *how* to use this plugin."""
    threaded = True

    def _convert_timestamp(self, timestamp):
        dt = datetime.datetime.fromtimestamp(timestamp)
        age = datetime.datetime.now() - dt

        plural = lambda n: 's' if n > 1 else ""

        if age.days:
            age = '%s day%s ago' % (age.days, plural(age.days))
        elif age.seconds > 3600:
            hours = age.seconds / 3600
            age = '%s hour%s ago' % (hours, plural(hours))
        elif 60 <= age.seconds < 3600:
            minutes = age.seconds / 60
            age = '%s minute%s ago' % (minutes, plural(minutes))
        elif 30 < age.seconds < 60:
            age = 'less than a minute ago'
        else:
            age = 'less than %s second%s ago' % (d.seconds, plural(d.seconds))
        # str_dt = dt.strftime('%Y-%m-%d %I:%M %p')
        return age

    def np(self, irc, msg, args, nick):
        """[nick]

       Show currently playing movie/show from TraktTV. Needs to be a public
       profile. If no nick is supplied the IRC nick of the caller is attempted.""" 

        if not nick:
            nick = msg.nick

        apikey = self.registryValue('apikey')
        outurl = self.registryValue('outurl')
        username = self.registryValue('username')
        passwordhash = self.registryValue('passwordhash')
        params = {'username': username, 'password': passwordhash}

        if not apikey or apikey == "Not set":
            irc.reply("API key not set. see 'config help supybot.plugins.TraktTV.apikey'.")
            return

        #url = "http://api.trakt.tv/user/watching.json/%s/" % apikey
        url = "http://api.trakt.tv/user/profile.json/%s/" % apikey
        url += nick
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req, json.dumps(params))
            data = f.read()
        except urllib2.URLError, err:
            if err.code == 404:
                irc.reply("User not found.")
                return
        try:
            data = json.loads(data)
        except:
            irc.reply("Failed to parse response from trakt.tv.")
            raise
            return
        if len(data) == 0:
            irc.reply('No data available. Not a public profile?')
            return
        status = data.get('status')
        if status and status == 'error':
            widget = 'http://trakt.tv/user/%s/widget/watched-fanart.jpg' % nick
            irc.reply(data.get('message') + " Maybe check out " + widget)
            return

        watch = data.get('watching')
        watching = False
        if watch:
            watching = True
        else:
            watch = data.get('watched')

        if not watch or len(watch) < 1:
            irc.reply("%s have not seen anything." % nick)
            return

        if not watching:
            watch = watch[0]

        wtype = watch.get('type')
        
        movie = watch.get('movie')
        show = watch.get('show')
        ep = watch.get('episode')

        output = nick.encode('utf-8')
        t = ''
        if watching:
            output += ' np. '
        else:
            output += ' played ' 
            t = self._convert_timestamp(watch.get('watched'))
            t = ' ' + ircutils.bold(t)
        if wtype == 'episode':
            output += '{0} - {3} (s{1:02d}e{2:02d}){5} - {4}'.format(
                    ircutils.bold(show.get('title')),
                    ep.get('season'),
                    ep.get('number'), ep.get('title'),
                    ep.get('overview').encode('utf-8'),
                    t)
        elif wtype == 'movie':
            output += '{0} ({1}){3} - {2} '.format(
                    ircutils.bold(movie.get('title')).encode('utf-8'),
                    movie.get('year'),
                    movie.get('overview').encode('utf-8'),
                    t)
            if outurl:
                output += movie.get('url').encode('utf-8')
        irc.reply(output)

    np = wrap(np, [optional('text')])

Class = TraktTV


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
