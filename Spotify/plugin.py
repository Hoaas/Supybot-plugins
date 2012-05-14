# coding=utf8
###
# Copyright (c) 2010, Terje Hoås
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#	* Redistributions of source code must retain the above copyright notice,
#	  this list of conditions, and the following disclaimer.
#	* Redistributions in binary form must reproduce the above copyright notice,
#	  this list of conditions, and the following disclaimer in the
#	  documentation and/or other materials provided with the distribution.
#	* Neither the name of the author of this software nor the name of
#	  contributors to this software may be used to endorse or promote products
#	  derived from this software without specific prior written consent.
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

# This product uses a SPOTIFY API but is not endorsed, 
# certified or otherwise approved in any way by Spotify. 
# Spotify is the registered trade mark of the Spotify Group.

import urllib, urllib2
import json

import supybot.utils as utils
from supybot.commands import *
import supybot.conf as conf
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class Spotify(callbacks.Plugin):
	"""If a Spotify URI is posted, this plugin replies with Artist and Song
        name. Can reply with http-url aswell. May also use the Spotify API to
        reply with Artist and Song name on http-urls on open.spotify.com"""
	threaded = True
	
	
	# Warning. Will totally freeze up the bot if the url is to a page that require login.
	def doPrivmsg(self, irc, msg):
		channel = msg.args[0].lower()
		
		prefix = self.registryValue('prefix', channel)
		titleOnUrl = self.registryValue('titlewhenhttp', channel)
		outputurl = self.registryValue('outputurl', channel)
		
		if ircmsgs.isAction(msg):
			text = ircmsgs.unAction(msg)
		else:
			text = msg.args[1]
		text = text.split()
                # For each word
		for t in text:
			spotifytype = None
			httpurl = None
                        linkwashttp = False
			# Check for http and convert to Spotify URI
			if t.find("http://open.spotify.com/") != -1: # If not failure to find http-url
                                httpurl = t
                                linkwashttp = True
				if t.find("track/") != -1:
				    t = "spotify:track:" + t[t.find("track/")+6:]
				elif t.find("artist/") != -1:
				    t = "spotify:artist:" + t[t.find("artist/")+7:]
				elif t.find("album/") != -1:
				    t = "spotify:album:" + t[t.find("album/")+6:]
                                elif t.find("user/") != -1:
                                    t = "spotify:user:" + t[t.find("user/")+5:]
                                elif t.find("search/") != -1:
                                    t = "spotify:search:" + t[t.find("search/")+8:]
			# At this point t contains a spotify uri (not http).
			# Check for Spotify URI and set type
			if t.find("spotify:track") != -1:
			    spotifytype = "track"
			elif t.find("spotify:artist") != -1:
			    spotifytype = "artist"
			elif t.find("spotify:album") != -1:
			    spotifytype = "album"
                        elif t.find("spotify:user") != -1:
                            spotifytype = "user"
                        elif t.find("spotify:search") != -1:
                            spotifytype = "search"

			# If a type was found
			if spotifytype:
                            self.log.info('spotify uri detected, triggered by "%s".' % msg.prefix)

                            if linkwashttp and not titleOnUrl:
                                continue

			    # If we want to output http and it was a spotify URI
			    if outputurl and not linkwashttp:
			    	httpurl = "http://open.spotify.com/"
				httpurl += t.replace("spotify:", "").replace(":","/")

                            # HTTP now contains http://-uri and t contains spotify:-uri
                            
                            # Can not use api for user and search.
                            if spotifytype == "user" or spotifytype == "search":
                                irc.reply(httpurl)
                                continue

                            url = "http://ws.spotify.com/lookup/1/.json?uri=" + urllib.quote(t)
	    		    try:
    			        url.encode('utf-8')
			        req = urllib2.Request(url)
			        f = urllib2.urlopen(req)
			        jsonstr = f.read()
			    except urllib2.HTTPError as err:
			        self.log.debug(str(err))
                                # If the plugin should have replied
                                if err.code == 200:
                                    pass # OK
                                elif err.code == 304:
                                    pass # Not Modified
                                elif err.code == 400:
                                    # Bad Request
                                    irc.reply("Spotify API did not understand. Bad Request. Probably a bug in the plugin.")
                                elif err.code == 403:
                                    # Forbidden
                                    irc.reply("Spotify API says NO. You have to wait 10 seconds. (or more, see https://developer.spotify.com/technologies/web-api/#rate-limiting)")
                                elif err.code == 404:
                                    # Not Found
                                    irc.reply("Spotify API not found, error 404 etc.")
                                elif err.code == 406:
                                    # Not Acceptable
                                    irc.reply('Spotify API says "No! Not Acceptable.". Probably a bug in the plugin.')
                                elif err.code == 500:
                                    # Internal Server Error
                                    irc.reply("Spotify API had an Internal Server Error. Might be aliens.")
                                elif err.code == 503:
                                    # Service Unavailable
                                    irc.reply("Spotify API temporarily unavailable.")
                                else:
                                    irc.reply("Spotify API returned error " + err.code)
                                continue

                            try:
			        j = json.loads(jsonstr)
                            except:
                                irc.reply("Failed to read JSON from Spotify API")
                                continue
				
			    ## Full JSON for debugging, with pretty formating.
			    # print "--------- This is the full json ---------"
			    # print json.dumps(j, sort_keys=True, indent=4)
			    # print "--------- That was it! ---------"
                            reply = ""
			    if spotifytype == "track":
			        track = j["track"]["name"]
				artist = None
				for a in j["track"]["artists"]:
			            if artist is None:
		                        artist = a["name"]
				    else:
				        artist += ", " + a["name"]
				reply = prefix + " " + artist + " - " + track
						
			    elif spotifytype == "artist":
			        artist = j["artist"]["name"]
				reply = prefix + " " + artist
						
			    elif spotifytype == "album":
			        artist = j["album"]["artist"]
				album = j["album"]["name"]
				reply = prefix + " " + artist + " - " + album

                            if outputurl and not linkwashttp:
			        reply += " (" + httpurl + ")"
                            if reply != "":
			        irc.reply(reply.encode('utf-8'))
                            else:
                                self.log.warning("Plugin read JSON just fine, but failed to find any output. This is probably a bug.")


Class = Spotify


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
