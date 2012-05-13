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

import urllib2
import json

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks


class NTNUCourses(callbacks.Plugin):
    """This plugin returns course codes and names when inputet a full or partial course code.
    For Norwegian University of Science and Technology (NTNU). Uses http://www.ime.ntnu.no/api/."""
    threaded = True


    def course(self, irc, msg, args, course):
        """<course code>

        Returns name and course code on the first course that matches the full or partial course code."""

        channel = msg.args[0]

        if self.registryValue('norwegian', channel):
            url = 'http://www.ime.ntnu.no/api/course/no/'    # URL for Norwegian names
        else:
            url = 'http://www.ime.ntnu.no/api/course/en/'    # URL for English names
        url = url + course

        ref = 'irc://%s/%s' % (dynamic.irc.server, dynamic.irc.nick)
        try:
            req = urllib2.Request(url)
            req.add_header(ref, 'https://github.com/Hoaas/Supybot-plugins/')
            f = urllib2.urlopen(req)
            html = f.read()
        except:
            irc.reply("No information. Possibly not a valid course code, or API is offline.")
            return

        try:
            j = json.loads(html)
        except ValueError as err:
            #irc.reply(str(err))
            pass

        ## Full JSON for debugging, with pretty formating.
        # print "--------- This is the full json ---------"
        # print json.dumps(j, sort_keys=True, indent=4)
        # print "--------- That was it! ---------"
        reply = None
        try:
            reply = j["course"]["code"] + " - " + j["course"]["name"]
        except:
            reply = "404 - course not found."
        irc.reply(reply.encode('utf-8'))
    course = wrap(course, ['text'])


Class = NTNUCourses


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
