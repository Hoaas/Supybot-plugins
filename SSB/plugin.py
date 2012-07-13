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
import re
import urllib, urllib2
import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
from supybot.i18n import PluginInternationalization, internationalizeDocstring

_ = PluginInternationalization('SSB')

@internationalizeDocstring
class SSB(callbacks.Plugin):
    """Add the help for "@plugin help SSB" here
    This should describe *how* to use this plugin."""
    threaded = True

    def fornavn(self, irc, msg, args, name):
        """<navn>

        Returnerer antall som har dette som fornavn."""
        
        name = name.capitalize()
        furl, murl = self._geturls(firstname=name, lastname=None)
        female = self._fetch_and_strip(furl)
        male = self._fetch_and_strip(murl)

        female = female.replace('<br>', '').strip()
        male = male.replace('<br>', '').strip()

        if female.find('3, 2, 1') != -1:
            female = None
        else:
            d = re.compile('\d+')
            female = int(d.findall(female)[0])

        if male.find('3, 2, 1') != -1:
            male = None
        else:
            d = re.compile('\d+')
            male = int(d.findall(male)[0])

        output = ""
        if female:
            output += '{0} kvinner som har {1} som første fornavn. '.format(female, name)
        if male:
            output += '{0} menn som har {1} som første fornavn.'.format(male, name)

        if not male and not female:
            irc.reply('3, 2, 1 eller 0 som har {0} som første fornavn.'.format(name))
            return
        irc.reply(output)
    fornavn = wrap(fornavn, ['text'])

    def etternavn(self, irc, msg, args, name):
        """<navn>

        Returner antall som har dette som etternavnet."""
        name = name.capitalize()
        url, _= self._geturls(firstname=None, lastname=name)
        etternavn = self._fetch_and_strip(url)
        irc.reply(etternavn)
    etternavn = wrap(etternavn, ['text'])

    def navn(self, irc, msg, args, name):
        """<etternavn, fornavn>

        Returnerer info om navnet. Komma må brukes for å skille etternavn og
        fornavn."""
        if name.find(',') == -1:
            irc.error()

        name = name.split(',')
        name[0] = name[0].strip().capitalize()
        name[1] = name[1].strip().capitalize()
        if not name[0] or not name [1]:
            irc.error()

        urlf, urlm = self._geturls(firstname=name[1],
                lastname=name[0])


        output = 0

        data = self._fetch_and_strip(urlf)
        data = data.replace('<br>', '')
        sentences = data.split('.')
        for s in sentences:
            if s.find('etternavn') != -1 and s.find('fornavn') != -1:
                if s.find('3, 2, 1') == -1:
                    irc.reply(s + '. ')
                    output += 1

        data = self._fetch_and_strip(urlm)
        data = data.replace('<br>', '')
        sentences = data.split('.')
        for s in sentences:
            if s.find('etternavn') != -1 and s.find('fornavn') != -1:
                if s.find('3, 2, 1') == -1:
                    irc.reply(s + '.')
                    output += 1

        if output == 0:
            irc.reply('Det er 3, 2, 1 eller 0 personer som har {0} som første fornavn, og {1} som etternavn.'.format(name[1], name[0]))

    navn = wrap(navn, ['text'])

    def _geturls(self, firstname=None, lastname=None):
        url = 'http://www.ssb.no/navn/sok.cgi?'# lang=n&'
        params = {}
        if firstname:
            params['fornavn'] = firstname.decode('utf8').encode('latin1')
        if lastname:
            params['etternavn'] = lastname.decode('utf8').encode('latin1')
        url += urllib.urlencode(params)
        url2 = None
        if firstname:
            url2 = url
            url += '&base=kvinne'
            url2 += '&base=mann'
        return url, url2

    def _fetch_and_strip(self, url):
        try:
           req = urllib2.Request(url)
           req.add_header('Supybot plugin (IRC-bot)', 'https://github.com/Hoaas/Supybot-plugins/tree/master/SSB')
           f = urllib2.urlopen(req)
           html = f.read()           
        except:
            return None
        finally:
            try:
                f.close()
            except NameError:
                pass

        start = '</b><p>'
        start = html.find(start) + len(start)
        stop = '</td><td>'
        stop = html.find(stop) + len(stop)
        html = html[start:stop].strip()

        html = html.replace('\n', '')
        html = html.replace('<p>', '')
        #html = html.replace('<br>', '')
        html = html.replace('<td>', '')
        html = html.replace('</td>', '')
        return html
    
    def gender(self, irc, msg, args, name):
        """<navn>

        Returnerer hvor mange prosent av hvert kjønn som har dette navnet."""
        url1, url2 = self._geturls(firstname=name, lastname=None)

        female = self._fetch_and_strip(url1)
        male = self._fetch_and_strip(url2)

        if female.find('3, 2, 1') != -1:
            female = None
        else:
            d = re.compile('\d+')
            female = int(d.findall(female)[0])

        if male.find('3, 2, 1') != -1:
            male = None
        else:
            d = re.compile('\d+')
            male = int(d.findall(male)[0])

        if not male and not female:
            irc.reply('Ikke nok mennesker i Norge som har det navnet. (3, 2, 1 eller 0)')
            return
        if not male:
            male = 0
        if not female:
            female = 0

        tot = float(female + male)
        fprc = float(female)*100 / tot 
        mprc = float(male)*100 / tot

        output = '{0}: {1:.1f}% kvinner, {2:.1f}% menn. ({3} : {4})'.format(name, fprc, mprc, female, male)
        irc.reply(output)
    gender = wrap(gender, ['text'])

Class = SSB


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
