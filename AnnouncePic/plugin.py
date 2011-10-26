# coding=utf8
###
# Copyright (c) 2011, Terje Hoås
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

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot import ircmsgs
import supybot.ircdb as ircdb
import supybot.conf as conf

import re
import time
import threading
import os

class AnnouncePic(callbacks.Plugin):
    """This plugin monitors a local folder and announces when a file have been added."""

    def __init__(self, irc):
        self.__parent = super(AnnouncePic, self)
        self.__parent.__init__(irc)
        self.e = threading.Event()
        self.started = threading.Event()
        self.url = "http://hoaas.net/pics/voll/"
        self.path = "/home/hoaas/www/hoaas.net/pics/voll/"
        self.channel = "#voll"
        self._makeDb()

    def _makeDb(self):
        dataDir = conf.supybot.directories.data
        self.dbloc = dataDir.dirize("/AnnouncePic.db")
        if not os.path.isfile(self.dbloc):
            open(os, 'w')


    def _monitorFolders(self, irc):
        while not self.e.isSet():
            db = open(self.dbloc, 'r')
            files = db.read() # Files listed in registry
            db.close()
    
            filelist = self._splitter(files) # Splits them into a file list
            dirlist = os.listdir(self.path) # Files actually on disc

            newfiles = set(dirlist) - set(filelist)
            output = None
            for n in newfiles:
                output = self.url + n + " "
            if output:
                print "New files added in watchfolder. Outputting to channel."
                irc.queueMsg(ircmsgs.privmsg(self.channel, output))
            if newfiles: # Should only happen when output is present aswell. but meh.
                db = open(self.dbloc, 'w')
                db.write(self._joiner(dirlist))
                db.close()
            time.sleep(60) # Waiting 60 seconds.
        self.started.clear()

    def _splitter(self, s):
        return re.split(r'\s*,\s*', s)

    def _joiner(self, s):
        ret = "" # return stirng
        for f in s: # for all filenames
            ret += f + " , " # Add filename and " , " to returnstring
        ret = ret[:-3] # Remove the last 3 chars from the returnstring, as they are " , "
        return ret

    def start(self, irc, msg, args):
        """Start monitoring local folders."""
        if not self.started.isSet():
            self.e.clear()
            self.started.set()
            t = threading.Thread(target=self._monitorFolders,
                                 kwargs={'irc':irc})
            t.start()
            irc.reply("Monitoring start successful. Now reporting new files added.")
        else:
            irc.error("Monitoring already started.")
    start = wrap(thread(start))

    def stop(self, irc, msg, args):
        irc.reply("Stopping local folder monitoring.")
        self.e.set()
    stop = wrap(stop)

    def die(self):
        self.e.set()
        self.__parent.die()




Class = AnnouncePic


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
