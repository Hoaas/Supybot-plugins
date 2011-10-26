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
import urllib, urllib2

import sys
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class WTFSIMFD(callbacks.Plugin):
    """Add the help for "@plugin help WTFSIMFD" here
    This should describe *how* to use this plugin."""
    threaded = True
    
    def dinner(self, irc, msg, args):
        """

        What The Fuck Should I Make For Dinner? HOW ABOUT SOME FUCKING ...
        """
        
        url = "http://www.whatthefuckshouldimakefordinner.com/"
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            html = f.read()
        except:
            irc.reply("Can't read " + url + " at this point.")
            return
        html = html[html.find("<dl>")+4:]
        insult = html[:html.find("</dl>")].strip()
        
        html = html[html.find("<dl>")+4:]
        html = html[html.find("<a href=\"")+9:]
        dinnerurl = html[:html.find("\"")].strip()
        
        html = html[html.find(">")+1:]
        dinner = html[:html.find("</a>")].strip()
        irc.reply(insult + " " + dinner + ". (" + dinnerurl + ")")
    dinner = wrap(dinner)
    
    def fp(self, irc, msg, args):
    	"""
    	
    	Gets the picture of todays food from foodporndaily.com
    	"""
   	
    	url = "http://foodporndaily.com/"
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            html = f.read()
        except:
            irc.reply("Can't read " + url + " at this point.")
            return
        str = 'img id="mainPhoto" src="'
        html = html[html.find(str)+len(str):]
        imageurl = html[:html.find('"')]

        # This part is for shortening the url. Not really needed.
        """
        url = "http://is.gd/api.php?longurl=" + imageurl
        print "Trying to shorten url using " + url
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            imageurl = f.read()
        except:
            print "Failed to shorten url: " + url
            return
        """
        """
        # This part is all for downloading the images, using the ImgGet plugin, if loaded.
    	imgget = False
    	try:
    		sys.modules['ImgGet']
    		imgget = True
    	except:
    		pass
    	if imgget:
            try:
                connection = urllib.urlopen(imageurl)
                # Try to get content-type from header
                contenttype = connection.info().getheader("Content-Type")
	            # If we actually have a type, and it claims to be an image, we continue.
            except:
                print "Could not open connection or get header from " + url
            if contenttype and contenttype.startswith('image'):
	            # print sys.modules['ImgGet']._downloadImg(irc, imageurl, irc.nick, msg.args[0].lower(), connection, contenttype)
        """
        irc.reply(imageurl)
    fp = wrap(fp)
Class = WTFSIMFD


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
