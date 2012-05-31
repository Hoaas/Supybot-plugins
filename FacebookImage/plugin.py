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
    of the poster and the URL to the album. Can also be checked manually with
    the facestalk command. This command will attempt to find a facebook-type 
    picture filename in all words. If the word 'facestalk' appears the auto-check
    will automaticly yield."""
    threaded = True
    
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0].lower()
        enabled = self.registryValue('enable', channel)
        if not enabled:
           return
        # If the command is called, this must be ignored, or the output will come twice.
        if msg.args[1].find("facestalk") != -1:
            return
        for url in utils.web.urlRe.findall(msg.args[1]):
            if((url.endswith(".jpg") or url.endswith(".jpg?dl=1")) and "fbcdn" in url):
                self._replyStalk(irc, url)

    def _replyStalk(self, irc, word):
        filename = word.split("/")[-1]
        name, uid, albumid = self._getNameAndID(filename)
        # With no UID we got nothing
        if not uid:
            return False
        # With UID but without albumid we most likely got a profile picture
        elif albumid == -1:
            irc.reply("Profile picture of {0} (https://www.facebook.com/profile.php?id={1})".format(name, uid))
            return True
        elif not albumid.isdigit(): # Image from a Page of some sort.
            irc.reply("By {0} ({1})".format(name, albumid))
            return True
        # This might possibly happen because of a new format.
        if not name:
            irc.reply("In this album: https://www.facebook.com/photo.php?fbid={}".format(uid))
            return True
        # If we have everything it is probably a regular picture.
        irc.reply("By {0} (https://www.facebook.com/profile.php?id={2}) in this album: https://www.facebook.com/photo.php?pid={1}&id={2}".format(name, albumid, uid))
        return True

    def facestalk(self, irc, msg, args, words):
        """<text>
        If one of the words in the text ends with a facebook-style image filename 
        the name of the poster of the image will be returned in addition to link 
        to the profile and possibly a link to the album.
        Link to the album might be restricted according the the owners privacy settings.
        """
        found = False
        for word in words.split():
            if(word.endswith(".jpg") or word.endswith(".jpg?dl=1")):
                if self._replyStalk(irc, word):
                    found = True
        if not found:
            irc.reply("Could not find a facebook style file name.")
    facestalk = wrap(facestalk, ['text'])

    def _getNameAndID(self, filename):
        numbers = filename.split("_")
        # If it is a direct link to a profile picture
        if len(numbers) == 4:
            uid = numbers[1]
            albumid = -1
        # Normal picture
        elif len(numbers) == 6:
            uid = numbers[2]
            albumid = numbers[3]
        else:
            return None, None, None
        # If we don't have digits at this point the url was probably something different.
        if not uid.isdigit() and not albumid.isdigit():
            return None, None, None
        url = "http://graph.facebook.com/" + uid
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            jsonstr = f.read()
        except urllib2.HTTPError, err:
            self.log.warning("Facebook API returned " + str(err.code) + " for url " + url)
            return
        except urllib2.URLError, err:
            self.log.warning("Failed to load Facebook API. Possible timeout. Error: " + str(err))
            return
        j = json.loads(jsonstr)
        if j == False:
            # Happens with some images. Not 100% sure why. Might be a new
            # format
            if uid:
                return None, uid, None
            else:
                return None, None, None
        self.log.info(url)
        try:
            name = j["name"].encode('utf-8')
        except:
            # ugly ugly. For images by Pages. But not all.
            try:
                name = j["from"]["name"].encode('utf-8')
                uid = j["from"]["id"].encode('utf-8')
                albumid = j["link"].encode('utf-8')
            except:
                if uid:
                    return None, uid, None
                else:
                    return None, None, None
        return name, uid, albumid 


                        
Class = FacebookImage


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
