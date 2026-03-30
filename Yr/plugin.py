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
import json
from datetime import datetime
import pytz
import urllib.parse

from supybot import utils, plugins, ircutils, callbacks
from supybot.commands import *
try:
    from supybot.i18n import PluginInternationalization
    _ = PluginInternationalization('Yr')
except ImportError:
    # Placeholder that allows to run the plugin on a bot
    # without the i18n module
    _ = lambda x: x

class Yr(callbacks.Plugin):
    """This plugin fetches current information from yr.no (which is a site run by The Norwegian Meteorological Institute)
        for the appropriate location, assuming the correct URL have been set. The language returned is defined by the set URL."""
    threaded = True

    @wrap(['channel', 'text'])
    def temp(self, irc, msg, args, channel, location):
        """[#channel] <city>

        Searches for location from geonames.org and uses coordinates found there to the API on met.no"""

        name, adminname, country, lat, lon = self._searchByName(location)

        if (name is None):
            irc.error('"%s" not found at geonames.org' % (location))
            return

        forecast = self._forecastByCoordinates(lat, lon)

        irc.reply(forecast + ' (%s, %s, %s)' % (name, adminname, country))

    @wrap(['channel', 'text'])
    def sun(self, irc, msg, args, channel, location):
        """[#channel] <city>
        
        🌞
        """
        name, adminname, country, lat, lon = self._searchByName(location)

        today = datetime.today()
        tz = pytz.timezone("Europe/Oslo")
        tzaware = tz.localize(today, is_dst=None)

        offset = '+0%s:00' % (1 if tzaware.tzinfo._dst.seconds == 0 else 2)
        url = 'https://api.met.no/weatherapi/sunrise/3.0/sun?date=%s&lat=%s&lon=%s&offset=%s' \
            % (today.date(), lat, lon, urllib.parse.quote(offset))
        
        data = utils.web.getUrl(url)
        j = json.loads(data)

        sunrise = self._readTimeFromJson(j, 'sunrise')
        sunset = self._readTimeFromJson(j, 'sunset')
        #moonrise = self._readTimeFromJson(j, 'moonrise')
        #moonset = self._readTimeFromJson(j, 'moonset')

        sun = '☀⬆ %s ☀⬇ %s' % (sunrise, sunset)
        #moon = '🌙⬆ %s 🌙⬇ %s' % (moonrise, moonset)

        irc.reply('%s, (%s, %s, %s)' % (sun, name, adminname, country))

    def _readTimeFromJson(self, j, key):
        time = j.get('properties').get(key).get('time')
        if time is None:
            return '❓'

        time = datetime.fromisoformat(time)
        return time.strftime('%H:%M')

    def _searchByName(self, query):
        username = 'robogoat'
        url = 'http://api.geonames.org/searchJSON?username=%s&q=%s' % (username, urllib.parse.quote(query))
        data = utils.web.getUrl(url)

        j = json.loads(data)
        if j.get('totalResultsCount') == 0:
            return None, None, None, None, None

        hit = j.get('geonames')[0]

        lat = hit.get('lat')
        lon = hit.get('lng')
        name = hit.get('toponymName')
        adminname = hit.get('adminName1')
        country = hit.get('countryName')

        return name, adminname, country, lat, lon

    def _forecastByCoordinates(self, lat, lon):
        headers = {
            'User-Agent': '+SupybotIRCPlugin https://github.com/Hoaas/Supybot-plugins',
            'Authorization': "Basic YjFlMWJlNWQtMTg0ZC00ZTM0LTk2ZjUtZGQwZjgyZWZhZjZi"
        }

        try:
            # Nordic area only
            url = 'https://api.met.no/weatherapi/nowcast/2.0/complete?lat=%s&lon=%s' % (lat, lon)
            data = utils.web.getUrl(url, headers=headers)
        except Exception:
            url = 'https://api.met.no/weatherapi/locationforecast/2.0/compact?lat=%s&lon=%s' % (lat, lon)
            data = utils.web.getUrl(url, headers=headers)
       
        j = json.loads(data)
        prop = j.get('properties')
        ts = prop.get('timeseries')[0]

        time = ts.get('time')
        units = prop.get('meta').get('units')

        tsdata = ts.get('data')
        instant = tsdata.get('instant')
        next1h = tsdata.get('next_1_hours')
        
        # Add null checks
        if not next1h:
            return 'Værdata ikke tilgjengelig'
            
        symbol = next1h.get('summary', {}).get('symbol_code')
        rain = next1h.get('details', {}).get('precipitation_amount')

        details = instant.get('details')
        temp = details.get('air_temperature')
        windspeed = details.get('wind_speed')
        winddirection = details.get('wind_from_direction')
        humidity = details.get('relative_humidity')

        output = '%s' % (self.temp_format(temp, windspeed, 'no'))
        if (symbol):
            symbol_emoji = self.symbol_to_emoji(symbol)
            output += ' %s' % (symbol_emoji)

        if (windspeed):
            output += ' %s %s' % (windspeed, units.get('wind_speed'))

            if (winddirection):
                dirs = ["nord", "nord-nordøst", "nordøst", "øst-nordøst", "øst", "øst-sørøst", "sørøst", "sør-sørøst", "sør", "sør-sørvest", "sørvest", "vest-sørvest", "vest", "vest-nordvest", "nordvest", "nord-nordvest"]
                ix = int((winddirection + 11.25 / 22.5 - 0.02))
                output += ' fra %s' % format(dirs[ix % 16])
            output += '.'

        if (humidity):
            output += ' %s%s luftfuktighet.' % (humidity, units.get('relative_humidity'))

        if (rain):
            output += ' %s %s nedbør.' % (rain, units.get('precipitation_amount'))

        return output

    @wrap([additional('text')])
    def pollen(self, irc, msg, args, loc):
        """[<location>]
        Norwegian only. See "pollen list" for list of locations.
        """
        irc.reply('Se https://www.naaf.no/pollenvarsel/')

        return

        if (loc == "list"):
            irc.reply("1 Østlandet med Oslo, 2 Sørlandet, 3 Rogaland, 4 Hordaland, \
5 Sogn og Fjordane, 6 Møre og Romsdal, 7 Sentrale fjellstrøk i Sør-Norge, 8 Indre Østlandet, \
9 Trøndelag, 10 Nordland, 11 Troms, 12 Finnmark")
            return
        
        # Dictionary with locations
        locations = {1: "Østlandet med Oslo",
                2: "Sørlandet",
                3: "Rogaland",
                4: "Hordaland",
                5: "Sogn og Fjordane",
                6: "Møre og Romsdal",
                7: "Sentrale fjellstrøk i Sør-Norge",
                8: "Indre Østlandet",
                9: "Trøndelag",
                10: "Nordland",
                11: "Troms",
                12: "Finnmark"}
        if not loc:
            loc = self.registryValue('pollen', msg.args[0]) # Default value is 1.

        fail = False
        try:
            loc = int(loc)
            # If the parsing fails we jump to the except.
        # if location is not an integer
        except:
            for l in locations:
                # If we have location that containt the string
                # Using lower() to ignore case.
                if(locations[l].lower().find(loc.lower()) != -1):
                    loc = l
                    fail = False
                    break
                else:
                    fail = True
            # If we have gone through the loop and loc still isn't an integer the location is not found
        
        # If number is outside the accepted range.
        if(not fail and (loc < 1 or loc > 12)):
            fail = True
        if fail:
            irc.reply('Sorry, ' + str(loc) + ' is not a valid location. Check "pollen list" for list of locations.')
            return
        # At this point loc is an integer from 1 to 12
        retstr = self._pollen(locations, loc)
        if (retstr == -1):
            irc.reply('Sorry, failed to retrieve pollentriks.')
        else:
            irc.reply(retstr)

    def symbol_to_emoji(self, symbol):
        symbol = symbol\
            .replace('_', ' ')\
            .replace('night', '')\
            .capitalize()\
            .strip()
        s = symbol.lower()
        output = ' '
        if ('clearsky' in s):
            output += '☀'
        elif ('fair' in s):
            output += '🌤️'
        elif ('partlycloudy' in s):
            output += '🌤'
        elif ('fog' in s):
            output += '🌫️'
        elif ('cloudy' in s):
            output += '☁'
        elif ('showers' in s):
            output += '🌦️'
        elif ('thunder' in s):
            output += '⛈️'
        elif ('rain' in s):
            output += '🌧️'
        elif ('snow' in s):
            output += '🌨️'
        elif ('sleet' in s):
            output += '🌨️🌧️'
        else:
                output += '%s.' % (symbol)

        return output

    """Takes two floats and returns float or None"""
    def wind_chill(self, temp, wind):
        if not (temp < 10 and (wind*3.6) > 4.8):
            return None

        windchill = 13.12 + 0.6215 * temp- 11.37 * ((wind * 3.6)**0.16) + 0.3965 * temp * ((wind * 3.6)**0.16)
        return windchill

    def temp_format(self, temp, wind, lang):
        chill = ''
        windchill = None
        if wind:
            windchill = self.wind_chill(temp, wind)
        if windchill is not None:
            chill = '{0:.1f}°'.format(windchill)
            if windchill > 0:
                chill = ircutils.mircColor(str(chill), 'Red')
            else:
                chill = ircutils.mircColor(str(chill), 12)
            chill = ' ({0})'.format(chill)
        tempdesc = str(temp) + '°'
        if temp > 0:
            tempdesc = ircutils.mircColor(tempdesc, 'Red')
        else:
            tempdesc = ircutils.mircColor(tempdesc, 12)
        if lang != 'en':
            tempdesc = tempdesc.replace('.', ',')
            chill = chill.replace('.', ',')
        return '{0}{1}'.format(tempdesc, chill)

    def _pollen(self, locations, loc):
        # locations is the dictionary, loc is the integer
        url = "http://www.yr.no/pollen/"
        
        plants = {
            0: "Salix",
            1: "Bjørk",
            2: "Or",
            3: "Hassel",
            4: "Gress",
            5: "Burot"
        }
        
        html = utils.web.getUrl(url).decode()

        first = locations[loc]
        # Dropping everything before our first find
        html = html[html.find(first):]
        html = html[:html.find('</tr>')]
        name = html[:html.find('<')]
        
        html = html[html.find('<td'):]
        html = html.splitlines()
        
        plantcounter = 0
        today = {}
        tomorrow = {}
        for i in range(len(html)):
            if ((i % 2) == 0):
                if(html[i].find('class') != -1):
                    today[plantcounter] = html[i][html[i].find('title="')+7:html[i].find('" />')]
            else:
                if(html[i].find('class') != -1):
                    tomorrow[plantcounter] = html[i][html[i].find('title="')+7:html[i].find('" />')]
                plantcounter += 1
        rtoday = ""
        rtomorrow = ""
        for i in today:
            if "Beskjeden" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Light green")
            elif "Moderat" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Orange")
            elif "Kraftig" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Red")
            elif "Ekstrem" in today[i]:
                today[i] = ircutils.mircColor(today[i], "Brown")

            rtoday += plants[i] + " (" + today[i] + "), "
        for i in tomorrow:
            if "Beskjeden" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Light green")
            elif "Moderat" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Orange")
            elif "Kraftig" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Red")
            elif "Ekstrem" in tomorrow[i]:
                tomorrow[i] = ircutils.mircColor(tomorrow[i], "Brown")
            rtomorrow += plants[i] + " (" + tomorrow[i] + "), "
        rtoday = rtoday[:-2]
        rtomorrow = rtomorrow[:-2]
        if (len(rtoday) < 5):
            rtoday = ircutils.bold("I dag") + ": Clear! "
        else:
            rtoday = ircutils.bold("I dag") + ": " + rtoday + ". "
        if (len(rtomorrow) < 5):
            rtomorrow = ircutils.bold("I morgen") + ": Clear!"
        else:
            rtomorrow = ircutils.bold("I morgen") + ": " + rtomorrow + "."
        
        if not rtoday and not rtomorrow:
            return "Ingen pollen varslet."
        if not rtoday:
            return rtomorrow
        if not rtomorrow:
            return rtoday
        return locations[loc] + ": " + rtoday + rtomorrow

    @wrap([])
    def hotncold(self, irc, msg, args):
        """
        Lists the 3 hottest and 3 coldest places in Norway with their temperatures.
        """
        try:
            region_codes = ["NO-42", "NO-32", "NO-33", "NO-56", "NO-34", "NO-15", "NO-18", 
                           "NO-03", "NO-11", "NO-21", "NO-40", "NO-55", "NO-50", "NO-39", 
                           "NO-46", "NO-31"]
            
            base_url = 'https://moduler.yr.no/api/v0/forecast/currenthourextremes/temperature'
            
            # Fetch hottest places without region filtering
            hot_url = f'{base_url}?order=max&limit=3'
            hot_data = utils.web.getUrl(hot_url)
            hot_top3 = json.loads(hot_data)
            
            # Check if we got valid data
            if not hot_top3:
                irc.error("No temperature data available")
                return
            
            cold_places_all = []
            
            # Fetch coldest places for each region (skip NO-21)
            for region in region_codes:
                if region != "NO-21":
                    try:
                        cold_url = f'{base_url}?order=min&limit=3&regionCode={region}'
                        cold_data = utils.web.getUrl(cold_url)
                        cold_json = json.loads(cold_data)
                        cold_places_all.extend(cold_json)
                    except Exception:
                        # Skip region if fetch fails
                        continue
            
            if not cold_places_all:
                irc.error("No cold temperature data available")
                return
            
            # Sort and get top 3 coldest
            cold_places_all.sort(key=lambda x: x['temperature']['value'])
            cold_top3 = cold_places_all[:3]
            
            # Format hottest places
            hot_places = []
            for place in hot_top3:
                temp = place['temperature']['value']
                name = place['locationMetadata']['name']
                county = place['locationMetadata']['county']
                temp_str = f"{temp}°"
                colored_temp = ircutils.mircColor(temp_str, 'Red')
                hot_places.append(f"{name} ({county}) {colored_temp}")
            
            # Format coldest places
            cold_places = []
            for place in cold_top3:
                temp = place['temperature']['value']
                name = place['locationMetadata']['name']
                county = place['locationMetadata']['county']
                temp_str = f"{temp}°"
                colored_temp = ircutils.mircColor(temp_str, 12)  # Light blue
                cold_places.append(f"{name} ({county}) {colored_temp}")
            
            # Create output message
            hot_header = ircutils.mircColor("🔥 Varmest:", 'Red')
            cold_header = ircutils.mircColor("🧊 Kaldest:", 12)
            
            hot_str = f"{hot_header} {', '.join(hot_places)}"
            cold_str = f"{cold_header} {', '.join(cold_places)}"
            
            irc.reply(f"{hot_str} | {cold_str}")
            
        except Exception as e:
            irc.error(f"Failed to fetch temperature extremes: {str(e)}")

Class = Yr
