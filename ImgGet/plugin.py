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

import os
import base64
import datetime
import mimetypes
import http.client
import urllib.parse

import supybot.conf as conf
import supybot.utils as utils
import supybot.ircmsgs as ircmsgs
import supybot.plugins as plugins
import supybot.callbacks as callbacks
from supybot.commands import *

try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('ImgGet')
except ImportError:
    _ = lambda x: x

try:
    import PIL.Image as Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ImgGet(callbacks.Plugin):
    """Listens for URLs posted in channels. If the URL points to an image and
    the file is within the configured size limit, it is downloaded locally.
    Optionally reports image resolution, file size, and a mirror link when the
    download was slow."""
    threaded = True

    def __init__(self, irc):
        self.__parent = super(ImgGet, self)
        self.__parent.__init__(irc)

    def _filename(self, nick, channel, url, contenttype):
        dataDir = conf.supybot.directories.data

        chandir = dataDir.dirize(channel)
        if not os.path.exists(chandir):
            os.makedirs(chandir)

        chandir = dataDir.dirize(f'{chandir}/img')
        if not os.path.exists(chandir):
            os.makedirs(chandir)

        orgfilenamelist = urllib.parse.urlparse(url).path.rsplit('/', 1)
        orgfilenamelist = orgfilenamelist[-1].rsplit('.', 1)
        orgfilename = orgfilenamelist[0]

        orgfilename = base64.b64encode(orgfilename.encode('ascii')).decode()
        orgfilename = orgfilename[:orgfilename.find('=')]

        if len(orgfilename) > 200:
            orgfilename = orgfilename[:200]

        filetype = '.' + contenttype.replace('image/', '')

        now = datetime.datetime.now()
        nowstr = datetime.datetime.isoformat(now)
        filename = f'{nowstr}_{nick}_{orgfilename}{filetype}'
        filedir = dataDir.dirize(f'{chandir}/{filename}')

        return filedir, filename

    def sizeof_fmt(self, num):
        if num is None:
            return 'Unknown size'
        num = int(num)
        for x in ['bytes', 'KiB', 'MiB', 'GiB']:
            if num < 1024.0:
                return '%3.1f %s' % (num, x)
            num /= 1024.0
        return '%3.1f %s' % (num, 'TiB')

    def _downloadImg(self, irc, url, nick, channel, contenttype, headers):
        # Try to get content-length from header
        contentlength = None
        sizeFromHeaderFormatted = None
        try:
            contentlength = int([tup for tup in headers if tup[0] == 'Content-Length'][0][1])
            sizeFromHeaderFormatted = self.sizeof_fmt(contentlength)
        except (IndexError, ValueError, TypeError):
            self.log.debug('Could not retrieve contentlength from header; %s', url)

        # Skip download if content-length exceeds the configured limit.
        sizelimit = self.registryValue('sizelimit', channel)
        if contentlength and contentlength > (1024 * 1024 * sizelimit):
            self.log.debug('Image too big: %s. Url: %s', sizeFromHeaderFormatted, url)
            return

        filedir, filename = self._filename(nick, channel, url, contenttype)

        self.log.info('Downloading %s: %s', sizeFromHeaderFormatted, url)

        starttime = datetime.datetime.now()
        try:
            imgdata = utils.web.getUrl(url)
        except Exception as e:
            self.log.debug('Could not download file from %s: %s', url, e)
            return
        endtime = datetime.datetime.now()

        try:
            with open(filedir, 'wb') as fd:
                fd.write(imgdata)
        except OSError as e:
            self.log.debug('Could not write downloaded file %s: %s', filedir, e)
            return

        secondsfloat = (
            float((endtime - starttime).seconds)
            + float((endtime - starttime).microseconds) / 1_000_000
        )
        speed = None

        if contentlength:
            contentlength = float(contentlength)
            speed = contentlength / secondsfloat
            self.log.info('Downloaded in %.2f seconds at %.2f KiB/s.', secondsfloat, speed / 1024)
        else:
            self.log.info('Downloaded in %.2f seconds.', secondsfloat)

        timelimit = self.registryValue('timelimit', channel)
        speedlimit = self.registryValue('speedlimit', channel)
        CUTOFF = 1024 * 1024 * 10

        mirror = False
        if secondsfloat > timelimit:
            if contentlength and contentlength < CUTOFF:
                mirror = True
            elif speed and speed < speedlimit:
                mirror = True
            elif not (contentlength and speed):
                mirror = True
            else:
                mirror = False
        if not self.registryValue('mirror', channel):
            mirror = False

        mirroroutput = ''
        if mirror:
            filename = urllib.parse.quote(filename)
            mirrorurl = self.registryValue('mirrorurl', channel)
            if mirrorurl == 'Not set':
                mirroroutput = 'Attempted to link to mirror, but mirror url for this channel is not set.'
                return
            if mirrorurl[-1] != '/':
                mirrorurl += '/'
            isgd_url = f'https://is.gd/create.php?format=simple&url={mirrorurl}{filename}'
            self.log.debug('Trying to shorten url using %s', isgd_url)
            try:
                isgdurl = utils.web.getUrl(isgd_url).decode()
            except Exception as e:
                self.log.warning('Failed to shorten url %s: %s', isgd_url, e)
                return
            self.log.info('Alt. source: %s Org. url took %.2f seconds to download.', isgdurl, secondsfloat)
            mirroroutput = f'Alt. source: {isgdurl} Org. url took {secondsfloat:.2f} seconds to download.'

        size = os.stat(filedir).st_size
        sizeFormatted = self.sizeof_fmt(size)

        if HAS_PIL:
            try:
                image = Image.open(filedir)
                width, height = image.size
                if sizeFormatted:
                    imageinfo = f'{width} \u00d7 {height} ({sizeFormatted})'
                else:
                    imageinfo = f'{width} \u00d7 {height}'
            except Exception as e:
                self.log.debug('PIL could not open image %s: %s', filedir, e)
                imageinfo = sizeFormatted or 'Unknown size'
        else:
            imageinfo = sizeFormatted or 'Unknown size'

        outputInfo = self.registryValue('outputInfo', channel)
        if outputInfo and not mirror:
            return imageinfo
        elif outputInfo and mirror:
            return f'{imageinfo} ({mirroroutput})'
        elif not outputInfo and mirror:
            return mirroroutput

    def _checkUrl(self, irc, text, nick, channel):
        for url in utils.web.urlRe.findall(text):
            contenttype = mimetypes.guess_type(urllib.parse.urlparse(url).path)[0]

            if not (contenttype and contenttype.startswith('image')):
                continue

            try:
                conn = http.client.HTTPConnection(urllib.parse.urlparse(url).netloc)
                conn.request('HEAD', urllib.parse.urlparse(url).path)
                res = conn.getresponse()
                headers = res.getheaders()
            except (http.client.HTTPException, OSError) as e:
                self.log.warning('Could not get header from %s: %s', url, e)
                continue

            reply = self._downloadImg(irc, url, nick, channel, contenttype, headers)
            if reply is not None:
                irc.reply(reply)

    def doPrivmsg(self, irc, msg):
        channel = msg.args[0].lower()

        if irc.isChannel(channel):
            if ircmsgs.isAction(msg):
                text = ircmsgs.unAction(msg)
            else:
                text = msg.args[1]

            self._checkUrl(irc, text, msg.nick, channel)


Class = ImgGet
