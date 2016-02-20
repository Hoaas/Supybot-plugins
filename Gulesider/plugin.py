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
        try:
            request = urllib.request.Request(url)
            response = urllib.request.urlopen(request)
            html = response.read().decode('utf-8')
            #html = utils.web.getUrl(url)
        except urllib.error.HTTPError as e:
            html = e.read()
        return html

    def formataddress(self, p):
        return ', '.join([_f for _f in (ircutils.bold(p.name), p.address()) if _f])

    def parsepersons(self, soup):
        persons = []
        hits = soup.find_all(class_='hit-header-block-center')
        for hit in hits:
            name = tlf = zipcode = location = street = None
            namefield = hit.find(class_='hit-name')
            if namefield:
                name = namefield.find('a').text.replace('\n', '')
            tlffield = hit.find(class_='hit-address')
            if tlffield:
                tlffield2 = tlffield.find(class_='hit-phone-number')
                if tlffield2:
                    tlf = tlffield2.text
            streetfield = hit.find(class_='hit-street-address')
            if streetfield:
                street = streetfield.text.replace('\n', '')
            zipcodefield = hit.find(class_='hit-postal-code')
            if zipcodefield:
                zipcode = zipcodefield.text
            locationfield = hit.find(class_='hit-address-locality')
            if locationfield:
                location = locationfield.text
            if not name and not tlf and not zipcode and not location and not street:
                continue
            p = Person(name, tlf, zipcode, location, street)
            persons.append(p)
        return persons

    def tlf(self, irc, msg, args, text):
        """<name | number>

        Henter informasjon fra gulesider.no. Sjekker også en lokal kopi av telefonterror.no."""
        isdigit = self.isdigit(text)
        if isdigit:
            terror = self.tlfterror(text)
            if terror:
                irc.reply(ircutils.bold(terror) + ', ifølge telefonterror.no')
                return
        html = self.fetch(text)
        soup = BS(html, 'lxml')

        persons = self.parsepersons(soup);
        if len(persons) == 0:
            irc.reply('No hits.')
            return
        lines = []
        for p in persons:
            if isdigit:
                lines.append(self.formataddress(p))
            else:
                lines.append(p.tlf + ' - ' + self.formataddress(p))
        ret = '; '.join([_f for _f in (l for l in lines) if _f])
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

class Person:
    def __init__(self, name, tlf, zipcode, location, street):
        self.name = name
        self.tlf = tlf
        self.zipcode = zipcode
        self.location = location
        self.street = street
    def address(self):
        loc = ' '.join([_f for _f in (self.zipcode, self.location) if _f])
        loc = ', '.join([_f for _f in (self.street, loc) if _f])
        return loc
