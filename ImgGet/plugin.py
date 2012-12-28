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

import datetime
import os.path
import simplejson
import base64
import PIL.Image as Image

import urllib, urllib2
import supybot.conf as conf
import supybot.utils as utils
from supybot.commands import *
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class ImgGet(callbacks.Plugin):
    """This plugin checks all urls said in channels or messages. If the url is an image (or apina.biz- or imgur.com-url) and the 
    image is less than 5 MiB it will be downloaded. If the download takes more than a set amount of seconds (default: 10) it will use is.gd
    to create a shortlink to http://defaultimgurl.com/img/filename"""
    threaded = True
    
    def __init__(self, irc):
        self.__parent = super(ImgGet, self)
        self.__parent.__init__(irc)
    
    def gis(self, irc, msg, args, options, search):
        """[--num int] [--urlonly] <search>

        I'm Feeling Lucky function for Google image search. 
        """

        ref = 'irc://%s/%s' % (dynamic.irc.server, dynamic.irc.nick)
        
        # Replaces all spaces with +. urllib2 doesn't like spaces.
        q = search.replace(" ", "+")
        v = "1.0"
        userip = irc.state.nickToHostmask(msg.nick)
        hl = "en"
        start = "0"
        safe = "off"
        
        values = {'v' : v,
                  'safe' : safe,
                  'hl' : hl,
                  'start' : start,
                  'q' : q }
        data = urllib.urlencode(values)
        url = "http://ajax.googleapis.com/ajax/services/search/images"
        url = url + "?" + data
        request = urllib2.Request(url, None, {'Referer': ref})
        
        try:
            response = urllib2.urlopen(request)
        except urllib2.HTTPError, e:
            self.log.debug(str(e))
            irc.reply("Could not connect to google at this point")
            return
        except urllib2.URLError, e:
            self.log.debug(str(e))
            irc.reply("Could not connect to google at this point")
            return
        except:
            self.log.debug("Unknown error in urllib2.")
            irc.reply("Could not connect to google at this point")
            return
        
        try:
            data = simplejson.load(response)
        except simplejson.JSONDecodeError, e:
            self.log.debug(str(e))
            irc.reply("Got a strange response from Google. *confused*")
            return
        
        if data['responseStatus'] != 200:
            self.log.debug(data['responseStatus'])
            raise callbacks.Error, 'We broke The Google!'
        num = False
        urlonly = False
        if options:
            for (key, value) in options:
                if key == 'num':
                    num = value
                if key == 'urlonly':
                    urlonly = True
        if not num:
            num = self.registryValue('numUrls', msg.args[0])

        if(len(data["responseData"]["results"]) > 0):
            if num < 1:
                num = 1
            elif num > 10:
                num = 10

            hits = []
            for key in range(len(data['responseData']['results'])):
                urldict = {}
                urldict['name'] = data['responseData']['results'][key]['content'].replace('<b>', '').replace('</b>', '')
                urldict['url'] = data['responseData']['results'][key]['unescapedUrl']
                hits.append(urldict)

            if num > len(hits):
                num = len(hits)
            added = 0
            output = ''
            for d in hits:
                if urlonly:
                    irc.reply(d['url'])
                else:
                    output +=  '%s: %s , ' % (ircutils.bold(d['name']), d['url'])
                added += 1
                if added >= num:
                    break
            if urlonly:
                return
            output = output[:-3]
            irc.reply(output)
            return
            # Disabled until I figure out how to handle this while outputting image info

            # Force checkurl, so we can download this image aswell.
            channel = msg.args[0].lower()
            if irc.isChannel(channel):
                if ircmsgs.isAction(msg):
                    text = ircmsgs.unAction(msg)
                else:
                    text = msg.args[1]

                self._checkUrl(irc, imgurl, irc.nick, channel)
        else:
            irc.reply("Your search did not match any documents.")
    gis = wrap(gis, [getopts({'num':'int', 'urlonly':''}), 'text'])
    
    def _apina(self, url):
        _, _, dotornot = url.partition("apina.biz/")
        
        # If there is no dot we can't continue
        if(dotornot.find(".") == -1):
            return -1
            
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            apinahtml = f.read()
            
            apinahtml = apinahtml.partition('<img src="')[2]
            apinahtml = apinahtml.partition('"')[0]
            url = apinahtml
        except:
            self.log.debug("Failed to retrieve img src from apina.biz-url.")
            url = -1
            
        return url

    def _filename(self, nick, channel, url, contenttype):
        dataDir = conf.supybot.directories.data
        
        chandir = dataDir.dirize(channel)
        if not os.path.exists(chandir):
            os.makedirs(chandir)
            
        chandir = dataDir.dirize(chandir + '/img')
        if not os.path.exists(chandir):
            os.makedirs(chandir)
        
        # Splits on the last /
        # example:
        # http://www.altenergystocks.com/assets/Nanotubes.jpg
        orgfilenamelist = url.rsplit('/', 1)
        # ['http://www.altenergystocks.com/assets', 'Nanotubes.jpg']
        orgfilenamelist = orgfilenamelist[-1].rsplit(".", 1)
        # ['Nanotubes', 'jpg']
        orgfilename = orgfilenamelist[0]

        # Probably should use some encoding tricks here instead.
        # There are lots of %-encodings.
        # Ok, decided to use base64-encoding instead. Should fix all the
        # XSS-holes and problems with filenames ending with %-stuff.
        orgfilename = base64.b64encode(orgfilename)
        
        # base64 adds some =s at the end.
        orgfilename = orgfilename[:orgfilename.find("=")]
        
        # orgfilename = orgfilename.replace(" ", "_")
        # orgfilename = orgfilename.replace("%20", "_")
        
        # Strip this a bit, to make sure it is below 255 chars in total (max on many file systems)
        if len(orgfilename) > 200:
        	orgfilename = orgfilename[200:]
        
        filetype = "." + contenttype.replace("image/", "")
        
        now = datetime.datetime.now()
        # Store date as string. YYYY-MM-DDTHH:MM:SS.ssssss
        nowstr = datetime.datetime.isoformat(now)
        filename = nowstr + '_' + nick + '_' + orgfilename  + filetype
        filedir = dataDir.dirize(chandir + '/' + filename)
        
        return filedir, filename
    
    def _imgur(self, url):
        try:
            req = urllib2.Request(url)
            f = urllib2.urlopen(req)
            imgurhtml = f.read()
            imgurhtml = imgurhtml.partition('<table><tr><td align="center"><a href="')[2]
            imgurhtml = imgurhtml.partition('"')[0]
            url = imgurhtml
        except:
            self.log.debug("Failed to retrieve img src from imgur.com-url.")
            url = -1
        return url

    def sizeof_fmt(self, num):
        if num is None:
            return 'Unknown size'
        num = int(num)
        for x in ['bytes','KiB','MiB','GiB']:
            if num < 1024.0:
                return "%3.1f %s" % (num, x)
            num /= 1024.0
        return "%3.1f %s" % (num, 'TiB')


    def _downloadImg(self, irc, url, nick, channel, connection, contenttype):
        # Try to get content-length from header
        contentlength = None
        size = None
        try:
            contentlength = int(connection.info().getheader("Content-Length"))
            size = self.sizeof_fmt(contentlength)
        except:
            self.log.debug('Could not retrieve contentlength from header; ' + url)
                                
        # We don't download if the contentlength is above 1 MiB * sizelimit. Download anyway if it doesn't say.
        sizelimit = self.registryValue('sizelimit', channel)
        if contentlength and contentlength > (1024*1024*sizelimit):
            self.log.debug('Image too big: %s. Url: %s' % (size, url))
            return
        
        # Create the image directory etc.
        filedir, filename = self._filename(nick, channel, url, contenttype)

        try: 
            self.log.info('Downloading %s: %s' % (size, url))
        except:
            self.log.debug("Downloading ??? KiB: " + url)
        
        
        # Starting the timer
        starttime = datetime.datetime.now()
        try:
            location, header = urllib.urlretrieve(url, filedir)
        except:
            self.log.debug('Could not download file from ' + url)
            return
        # Stopping the timer
        endtime = datetime.datetime.now()
        
        secondsfloat =  float((endtime - starttime).seconds)\
         + float((endtime - starttime).microseconds) / float(1000000)
        speed = None
        
        if(contentlength):
            contentlength = float(contentlength)
            speed = (contentlength / secondsfloat)
            self.log.info("Downloaded in %.2f seconds at %.2f KiB/s." % (secondsfloat, speed/1024))
        else:
            self.log.info("Downloaded in %.2f seconds." % secondsfloat)
            
        # If download took over timelimit seconds we link a mirror.
        timelimit = self.registryValue('timelimit', channel)
        speedlimit = self.registryValue('speedlimit', channel)
        
        CUTOFF = 1024*1024*10
        
        mirror = False
        if (secondsfloat > timelimit):
        # If it takes too long to open
        	if (contentlength and contentlength < CUTOFF):
        	# If it isn't over CUTOFF MiB.
        		mirror = True
        	elif (speed and (speed < speedlimit)):
        	# If the image is too big or size is unknown we check for speed
        		mirror = True
        	else:
        	# Takes too long, big filesize with high speed or unknown filesize and unknown speed.
        		if not (contentlength and speed):
        		# If we don't have both speed and size
        		# File might be very large with high speed, and mirror might not be faster
        			mirror = True
        		else:
        			mirror = False
        if not self.registryValue('mirror', channel):
            mirror = False

        mirroroutput = ''
        if(mirror):
            filename = urllib.quote(filename)
            mirrorurl = self.registryValue('mirrorurl', channel)
            if mirrorurl == "Not set":
                mirroroutput = "Attempted to link to mirror, but mirror url for this channel is not set."
                return
            if mirrorurl[-1] != "/":
               mirrorurl += "/"
            url = "http://is.gd/api.php?longurl=" + mirrorurl + filename
            self.log.debug("Trying to shorten url using " + url)
            try:
                requrl = urllib2.Request(url)
                urlf = urllib2.urlopen(requrl)
                isgdurl = urlf.read()
            except:
                self.log.warning("Failed to shorten url: " + url)
                return
            self.log.info("Alt. source: " + isgdurl + " Org. url took " + "%.2f" % secondsfloat + " seconds to download.")
            mirroroutput = "Alt. source: " + isgdurl + " Org. url took " + "%.2f" % secondsfloat + " seconds to download."
            #if not os.path.isfile(dataDir):
            #    open(dataDir, 'w')
 
        image = Image.open(location)
        width, height = image.size
        if size:
            imageinfo = '%s × %s (%s)' % (width, height, size)
        else:
            imageinfo = '%s × %s' % (width, height)
        
        outputInfo = self.registryValue('outputInfo', channel)
        if outputInfo and not mirror:
            irc.reply(imageinfo)
        elif outputInfo and mirror:
            irc.reply(imageinfo + ' (' + mirroroutput + ')')
        elif not outputInfo and mirror:
            irc.reply(mirroroutput)

        
    def _checkUrl(self, irc, text, nick, channel):
        for url in utils.web.urlRe.findall(text):
            # Incase of apina or imgur-urls we do some extra tricks.
            if(url.startswith("http://apina.biz/")):
                url = self._apina(url)
            elif(url.startswith("http://imgur.com/")):
                url = self._imgur(url)
            
            # If url was apina.biz or imgur.com, but not a picture we jump to next url.
            if(url == -1):
                continue
            
            # Try to open connection
            try:
                connection = urllib.urlopen(url)
            except:
                self.log.debug("Could not open connection to " + url)
                continue
            
            # Try to get content-type from header
            try:
                contenttype = connection.info().getheader("Content-Type")
            except:
                self.log.debug('Could not get header from ' + url)
                # Without a header we can't know if it is an image or not
                continue
    
            # If we actually have a type, and it claims to be an image, we continue.
            if contenttype and contenttype.startswith('image'):
                self._downloadImg(irc, url, nick, channel, connection, contenttype)
    
    # Warning. Do NOT have any check to see if an url to a big image is being spammed, or if that image is already downloaded.
    def doPrivmsg(self, irc, msg):
        channel = msg.args[0].lower()
       
        if irc.isChannel(channel):
            if ircmsgs.isAction(msg):
                text = ircmsgs.unAction(msg)
            else:
                text = msg.args[1]
                
            self._checkUrl(irc, text, msg.nick, channel)


Class = ImgGet


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
