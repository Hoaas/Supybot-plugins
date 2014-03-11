# coding=utf8
###
# Copyright (c) 2013, Terje Hoås
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
import urllib.request, urllib.parse, urllib.error
from xml.etree import ElementTree
from bs4 import BeautifulSoup as BS

import supybot.utils as utils
from supybot.commands import *
import supybot.plugins as plugins
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Gulesider')
except:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x:x

class Gulesider(callbacks.Plugin):
    """Add the help for "@plugin help Gulesider" here
    This should describe *how* to use this plugin."""
    threaded = True

    def isdigit(self, text):
        return text.replace('+', '').replace(' ', '').isdigit()

    def fetch(self, text):
        url = 'http://www.gulesider.no/person/resultat/'
        url += urllib.parse.quote(text)
        html = utils.web.getUrl(url)
        return html


    def getsinglehit(self, soup):
        hit = soup.find(class_='profile-main')
        if hit:
            return hit, 1
        return None, None

    def getmultiplehits(self, soup):
        hits = 0
        reslist = soup.find(id='result-list')
        if reslist:
            reslist = soup.find_all(class_='hit vcard')
            hits = len(reslist)
        return reslist, hits

    def fornavn(self, person):
        fornavn = person.find_all(class_='given-name')
        if not fornavn:
            return None
        elif len(fornavn) != 1:
            raise Exception('For mange fornavn!')
        return fornavn[0].text.strip()

    def mellomnavn(self, person):
        mellomnavn = person.find_all(class_='middleName')
        if not mellomnavn:
            return None
        elif len(mellomnavn) != 1:
            raise Exception('For mange mellomnavn! Evnt. for mange tags for mellomnavn på gulesider.no')
        return mellomnavn[0].text.strip()

    def etternavn(self, person):
        etternavn = person.find_all(class_='family-name')
        if not etternavn:
            return None
        elif len(etternavn) != 1:
            raise Exception('For mange etternavn!')
        return etternavn[0].text.strip()

    def getnavn(self, person):
        fornavn = self.fornavn(person)
        mellomnavn = self.mellomnavn(person)
        etternavn = self.etternavn(person)
        navn = ''
        if fornavn:
            navn += fornavn + ' '
        if mellomnavn:
            navn += mellomnavn + ' '
        if etternavn:
            navn += etternavn
        if navn == '':
            navn = None
        return navn.strip()

    def gettlf(self, person):
        tlf = person.find_all(class_='value')
        if not tlf:
            return None
        elif len(tlf) > 1:
            ret = []
            for t in tlf:
                ret.append(t.text.strip())
            return ' / '.join(ret)
        return tlf[0].text.strip()

    def getadresse(self, person):
        gate = person.find_all(class_='street-address')
        if gate and len(gate) > 0:
            gate = gate[0].text.strip()
        postnr = person.find_all(class_='postal-code')
        if postnr and len(postnr) > 0:
            postnr = postnr[0].text.strip()
        by = person.find_all(class_='locality')
        if by and len(by) > 0:
            by = by[0].text.strip()
        by = ' '.join([_f for _f in (postnr, by) if _f])
        return ', '.join([_f for _f in (gate, by) if _f])

    def formatperson(self, p, num):
        navn = self.getnavn(p)
        adresse = self.getadresse(p)
        tlf = ircutils.bold(self.gettlf(p))
        formatedperson = ''
        if num:
            formatedperson = ', '.join([_f for _f in (ircutils.bold(navn), adresse) if _f])
        else:
            navn_og_adresse = ', '.join([_f for _f in (navn, adresse) if _f])
            formatedperson = ' - '.join([_f for _f in (tlf, navn_og_adresse) if _f])
        return formatedperson


    def tlf(self, irc, msg, args, text):
        """<name | number>

        Henter informasjon fra gulesider.no"""

        num = self.isdigit(text)
        html = self.fetch(text)
        soup = BS(html)

        hits = 0
        persons, hits = self.getsinglehit(soup)
        if not persons:
            persons, hits = self.getmultiplehits(soup)

        if not persons or len(persons) == 0:
            if num:
                terror = self.tlfterror(text)
                if terror:
                    irc.reply(ircutils.bold(terror) + ', ifølge telefonterror.no')
                    return
            irc.reply('No hits.')
            return

        ret = ''
        if hits == 1:
            ret = self.formatperson(persons, num)
        else:
            for p in persons:
                ret = '; '.join([_f for _f in (ret, self.formatperson(p, num)) if _f])
        irc.reply(ret)
    tlf = wrap(tlf, ['text'])

    def tlfterror(self, num):
        path = os.path.dirname(__file__)
        liste = os.path.join(path, 'nummerliste.txt')

        num = num.replace(' ', '')
        if num.startswith('00'):
            num = '+' + num[2:]
        try:
            f = open(liste, encoding='windows-1252')
        except:
            self.log.warning('File nummerliste.txt from telefonterror.no is needed in the plugin directory for extended support.') 
            return
        for line in f:
            num_and_name = line.split(',')
            if len(num_and_name) != 2:
                continue
            if num_and_name[0] == num:
                return num_and_name[1].strip()


Class = Gulesider


# vim:set shiftwidth=4 softtabstop=4 expandtab textwidth=79:
