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
from lxml import etree
import urllib.request, urllib.error, urllib.parse, urllib.request, urllib.parse, urllib.error
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks

class DuckDuckGo(callbacks.Plugin):
    """This addon uses the search engine DuckDuckGos (@ duckduckgo.com) Zero-Click info.
    It extract info from a long range of sources, like wikipedia, IMDB and so forth.
    One example is simply searching for "h2o" will give you information about water. 
    See duckduckgo.com for more information."""
    threaded = True

    def ddg(self, irc, msg, args, query):
        """<query>

        Searches duckduckgo.com and returns any zero-click information, if any."""
        
        showurl = False
        safesearch = False
        maxreplies = 3
        showaddionalhits = False
        
        repliessofar = 0
        
        
        if safesearch:
            ss = "&kp=1"
        else:
            ss = "&kp=-1"
        #url = "https://api.duckduckgo.com/?format=xml&no_html=1&skip_disambig=1&no_redirect=1" + ss + "&q="
        url = "https://api.duckduckgo.com/?format=xml&no_html=1&no_redirect=1" + ss + "&q="
        query = urllib.parse.quote(query);
        url += query
        xml = utils.web.getUrl(url)

        # Dirty dirty hack to replace '<br>' with ' - '
        #xml = xml.replace("&lt;br&gt;", " - ")
        root = etree.fromstring(xml)
        try:
            root = etree.fromstring(xml)
        except:
            self.log.info("DDG: Crash.")
            return
        redirect = root.findtext("Redirect") 
        type = root.findtext("Type")
        answer = root.findtext("Answer")
        anstype = root.findtext("AnswerType")
        definition = root.findtext("Definition")
        defsrc = root.findtext("DefinitionSource")
        abstract = root.findtext("AbstractText")
        abstracturl = root.findtext("AbstractURL")
        abssrc = root.findtext("AbstractSource")
        results = root.findall("Results/Result")
        topics = root.findall("RelatedTopics/RelatedTopic")
        stopics = root.findall("RelatedTopics/RelatedTopicsSection/RelatedTopic")
        
        asrc = ""
        if abssrc:
            asrc = " ({0})".format(abssrc)
        dsrc = ""
        if defsrc:
            dsrc = " ({0})".format(defsrc)
        if answer and repliessofar < maxreplies:
            # TODO: Fix this. It looks ugly.
            if anstype:
                irc.reply(answer.strip() + "(" + anstype + ")")
            else:
                irc.reply(answer.strip())
            repliessofar += 1
        if abstract and repliessofar < maxreplies:
            # TODO: Fix this. It looks ugly.
            if showurl:
                output = abstract.strip() + " " + abstracturl.strip()
            else:
                output = abstract.strip() + asrc
            irc.reply(output)
            repliessofar += 1
            return
        if definition and repliessofar < maxreplies:
            irc.reply(definition.strip() + dsrc)
            repliessofar += 1
            return

        numresults = len(results)
        counter = 0
        while (counter < numresults) and (repliessofar < maxreplies):
            # TODO: Fix this. It looks ugly.
            if showurl:
                output = results[counter].findtext("Text") + " " + results[counter].findtext("FirstURL")
                output = output.strip()
            else:
                output = results[counter].findtext("Text") + asrc + dsrc
                output = output.strip()
            irc.reply(output)
            repliessofar += 1
            counter += 1

        topicsleft = len(topics)
        stopicsleft = len(stopics)
        totaltopics = topicsleft + stopicsleft
        
        i = 0
        while topicsleft > 0 and (repliessofar < maxreplies):
            if showurl:
                output = topics[i].findtext("Text") + " " + topics[i].findtext("FirstURL")
                output = output.strip()
            else:
                output = topics[i].findtext("Text") + asrc + dsrc
                output = output.strip()
            irc.reply(output)
            repliessofar += 1
            topicsleft -= 1
            i += 1
        i = 0
        while stopicsleft > 0 and (repliessofar < maxreplies):
            if showurl:
                output = stopics[i].findtext("Text") + " " + stopics[i].findtext("FirstURL")
                output = output.strip()
            else:
                output = stopics[i].findtext("Text") + asrc + dsrc
                output = output.strip()
            irc.reply(output)
            repliessofar += 1
            stopicsleft -= 1
            i += 1
    
        if repliessofar == maxreplies and totaltopics > repliessofar and showaddionalhits:
            irc.reply(str((numtopics + numstopics) - repliessofar) + " other topics.")
                # If there are only 1 topic
                # irc.reply(topics[0].findtext("Text") + " " + topics[0].findtext("FirstURL"))
        if redirect:
            irc.reply(redirect)
            repliessofar += 1
        if repliessofar == 0:
            irc.reply("No Zero-Click info from DuckDuckGo.")
              
    ddg = wrap(ddg, ['text'])
        

Class = DuckDuckGo


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
