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

import urllib2, json
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('FacebookImage')

@internationalizeDocstring
class FacebookImage(callbacks.Plugin):
    """Set config supybot.plugins.FacebookImage.enable to True, and every time
    someone posts a direct link to an image on facebook it will post the name
    of the poster and the URL to the album."""
    threaded = True
    
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0].lower()
        enabled = self.registryValue('enable', channel)
        if not enabled:
            return
        for url in utils.web.urlRe.findall(msg.args[1]):
            if(url.endswith("_n.jpg") and (url.startswith("http://fbcdn-sphotos-a.akamaihd.net") or
                    url.startswith("https://fbcdn-sphotos-a.akamaihd.net"))):
                filename = url.split("/")[-1]
                uid = filename.split("_")[2]
                albumid = filename.split("_")[3]
                url = "https://graph.facebook.com/" + uid
                try:
                    req = urllib2.Request(url)
                    f = urllib2.urlopen(req)
                    jsonstr = f.read()
                except urllib2.URLError, err:
                    self.log.warning("Facebook API returned " +
                            str(err.code) + " for url " + url)
                j = json.loads(jsonstr)
                name = j["name"]
                irc.reply("By {0} (http://www.facebook.com/photo.php?pid={1}&id={2})".format(j["name"].encode('utf-8'), albumid, uid))
                        
Class = FacebookImage


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
