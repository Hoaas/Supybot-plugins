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
import urllib.parse
from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import supybot.utils as utils
from supybot.commands import *
import supybot.ircutils as ircutils
import supybot.callbacks as callbacks
try:
    from supybot.i18n import PluginInternationalization, internationalizeDocstring
    _ = PluginInternationalization('Yr')
except ImportError:
    _ = lambda x: x
    internationalizeDocstring = lambda f: f


def searchByName(query):
    """Search geonames.org for a location by name.

    Returns (name, adminname, country, lat, lon) or (None, None, None, None, None)
    if no result is found.
    """
    username = 'robogoat'
    url = f'http://api.geonames.org/searchJSON?username={username}&q={urllib.parse.quote(query)}'
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


def parseForecast(data):
    """Parse a met.no nowcast/locationforecast JSON payload into a formatted string.

    data may be bytes or str. Returns a human-readable forecast string, or a
    translated error string if the required data is absent.
    """
    if isinstance(data, bytes):
        data = data.decode()
    j = json.loads(data)
    prop = j.get('properties')
    ts = prop.get('timeseries')[0]

    units = prop.get('meta').get('units')
    tsdata = ts.get('data')
    instant = tsdata.get('instant')
    next1h = tsdata.get('next_1_hours')

    if not next1h:
        return _('Weather data not available')

    symbol = next1h.get('summary', {}).get('symbol_code')
    rain = next1h.get('details', {}).get('precipitation_amount')

    details = instant.get('details')
    temp = details.get('air_temperature')
    windspeed = details.get('wind_speed')
    winddirection = details.get('wind_from_direction')
    humidity = details.get('relative_humidity')

    output = tempFormat(temp, windspeed)
    if symbol:
        output += f' {symbolToEmoji(symbol)}'

    if windspeed:
        output += f' {windspeed} {units.get("wind_speed")}'
        if winddirection is not None:
            dirs = [
                _('north'), _('north-northeast'), _('northeast'), _('east-northeast'),
                _('east'), _('east-southeast'), _('southeast'), _('south-southeast'),
                _('south'), _('south-southwest'), _('southwest'), _('west-southwest'),
                _('west'), _('west-northwest'), _('northwest'), _('north-northwest'),
            ]
            ix = int((winddirection + 11.25) / 22.5)
            output += f' {_("from")} {dirs[ix % 16]}'
        output += '.'

    if humidity:
        output += f' {humidity}{units.get("relative_humidity")} {_("humidity")}.'

    if rain:
        output += f' {rain} {units.get("precipitation_amount")} {_("precipitation")}.'

    return output


def forecastByCoordinates(lat, lon):
    """Fetch a weather forecast for the given coordinates.

    Tries nowcast (Nordic area) first, falls back to locationforecast.
    Returns the result of parseForecast().
    """
    headers = {
        'User-Agent': '+SupybotIRCPlugin https://github.com/Hoaas/Supybot-plugins',
        'Authorization': 'Basic YjFlMWJlNWQtMTg0ZC00ZTM0LTk2ZjUtZGQwZjgyZWZhZjZi',
    }

    try:
        url = f'https://api.met.no/weatherapi/nowcast/2.0/complete?lat={lat}&lon={lon}'
        data = utils.web.getUrl(url, headers=headers)
    except Exception:
        url = f'https://api.met.no/weatherapi/locationforecast/2.0/compact?lat={lat}&lon={lon}'
        data = utils.web.getUrl(url, headers=headers)

    return parseForecast(data)


def symbolToEmoji(symbol):
    """Convert a met.no symbol code to an emoji character."""
    symbol = symbol.replace('_', ' ').replace('night', '').capitalize().strip()
    s = symbol.lower()
    if 'clearsky' in s:
        return '☀'
    elif 'fair' in s:
        return '🌤️'
    elif 'partlycloudy' in s:
        return '🌤'
    elif 'fog' in s:
        return '🌫️'
    elif 'cloudy' in s:
        return '☁'
    elif 'showers' in s:
        return '🌦️'
    elif 'thunder' in s:
        return '⛈️'
    elif 'rain' in s:
        return '🌧️'
    elif 'snow' in s:
        return '🌨️'
    elif 'sleet' in s:
        return '🌨️🌧️'
    else:
        return f'{symbol}.'


def windChill(temp, wind):
    """Return wind chill temperature or None if conditions don't apply."""
    if not (temp < 10 and (wind * 3.6) > 4.8):
        return None
    return 13.12 + 0.6215 * temp - 11.37 * ((wind * 3.6) ** 0.16) + 0.3965 * temp * ((wind * 3.6) ** 0.16)


def tempFormat(temp, wind):
    """Format temperature with optional wind chill in IRC colour."""
    chill = ''
    if wind:
        windchill = windChill(temp, wind)
        if windchill is not None:
            chill_str = f'{windchill:.1f}°'
            if windchill > 0:
                chill_str = ircutils.mircColor(chill_str, 'Red')
            else:
                chill_str = ircutils.mircColor(chill_str, 12)
            chill = f' ({chill_str})'

    tempdesc = f'{temp}°'
    if temp > 0:
        tempdesc = ircutils.mircColor(tempdesc, 'Red')
    else:
        tempdesc = ircutils.mircColor(tempdesc, 12)

    return f'{tempdesc}{chill}'


def readTimeFromJson(j, key):
    """Extract and format a time value from a met.no sunrise JSON object."""
    time = j.get('properties', {}).get(key, {}).get('time')
    if time is None:
        return '❓'
    return datetime.fromisoformat(time).strftime('%H:%M')


def utcOffsetForTimezone(tz_name):
    """Return the current UTC offset for the given tz database name as an RFC 3339 string.

    E.g. 'Europe/Oslo' -> '+02:00', 'UTC' -> '+00:00'.
    Raises ZoneInfoNotFoundError if tz_name is not a valid tz database name.
    """
    tz = ZoneInfo(tz_name)
    now_local = datetime.now(tz)
    offset = now_local.utcoffset()
    total_minutes = int(offset.total_seconds() // 60)
    sign = '+' if total_minutes >= 0 else '-'
    total_minutes = abs(total_minutes)
    return f'{sign}{total_minutes // 60:02d}:{total_minutes % 60:02d}'


def formatTemperatureExtremes(hot_data, cold_region_data_list):
    """Format the hottest and coldest places from met.no temperature extremes data.

    hot_data: parsed JSON list of hottest places (already ordered, limit 3).
    cold_region_data_list: list of parsed JSON lists, one per region (order=min, limit 3).

    Returns a formatted IRC string, or None if either dataset is empty.
    """
    if not hot_data:
        return None

    cold_all = []
    for region_data in cold_region_data_list:
        cold_all.extend(region_data)

    if not cold_all:
        return None

    cold_all.sort(key=lambda x: x['temperature']['value'])
    cold_top3 = cold_all[:3]

    hot_parts = []
    for place in hot_data:
        temp = place['temperature']['value']
        name = place['locationMetadata']['name']
        county = place['locationMetadata']['county']
        hot_parts.append(f"{name} ({county}) {ircutils.mircColor(f'{temp}°', 'Red')}")

    cold_parts = []
    for place in cold_top3:
        temp = place['temperature']['value']
        name = place['locationMetadata']['name']
        county = place['locationMetadata']['county']
        cold_parts.append(f"{name} ({county}) {ircutils.mircColor(f'{temp}°', 12)}")

    hot_str = f"{ircutils.mircColor(_('🔥 Hottest:'), 'Red')} {', '.join(hot_parts)}"
    cold_str = f"{ircutils.mircColor(_('🧊 Coldest:'), 12)} {', '.join(cold_parts)}"
    return f'{hot_str} | {cold_str}'


# Regions used for cold extremes. NO-21 (Svalbard) is excluded because the
# API consistently returns no data for it.
_HOTNCOLD_REGIONS = [
    'NO-42', 'NO-32', 'NO-33', 'NO-56', 'NO-34', 'NO-15', 'NO-18',
    'NO-03', 'NO-11', 'NO-40', 'NO-55', 'NO-50', 'NO-39', 'NO-46', 'NO-31',
]


class Yr(callbacks.Plugin):
    """Fetches weather information from met.no / yr.no."""
    threaded = True

    @wrap(['channel', 'text'])
    @internationalizeDocstring
    def temp(self, irc, msg, args, channel, location):
        """[#channel] <city>

        Searches for location from geonames.org and uses coordinates found
        there to fetch a weather forecast from the met.no API."""
        name, adminname, country, lat, lon = searchByName(location)
        if name is None:
            irc.error(_('"%s" not found at geonames.org') % location)
            return
        forecast = forecastByCoordinates(lat, lon)
        irc.reply(f'{forecast} ({name}, {adminname}, {country})')

    @wrap(['channel', 'text'])
    @internationalizeDocstring
    def sun(self, irc, msg, args, channel, location):
        """[#channel] <city>

        Shows sunrise and sunset times for the given location."""
        name, adminname, country, lat, lon = searchByName(location)
        if name is None:
            irc.error(_('"%s" not found at geonames.org') % location)
            return

        tz_name = self.registryValue('timezone', channel)
        try:
            offset = utcOffsetForTimezone(tz_name)
        except ZoneInfoNotFoundError:
            irc.error(_('Unknown timezone: "%s"') % tz_name)
            return

        today = datetime.now(timezone.utc)
        url = f'https://api.met.no/weatherapi/sunrise/3.0/sun?date={today.date()}&lat={lat}&lon={lon}&offset={urllib.parse.quote(offset)}'
        data = utils.web.getUrl(url)
        j = json.loads(data)

        sunrise = readTimeFromJson(j, 'sunrise')
        sunset = readTimeFromJson(j, 'sunset')

        tz_label = f' ({tz_name})' if tz_name == 'UTC' else ''
        irc.reply(f'☀⬆ {sunrise} ☀⬇ {sunset}{tz_label}, ({name}, {adminname}, {country})')

    @wrap([])
    @internationalizeDocstring
    def hotncold(self, irc, msg, args):
        """

        Lists the 3 hottest and 3 coldest places in Norway with their
        temperatures."""
        base_url = 'https://moduler.yr.no/api/v0/forecast/currenthourextremes/temperature'

        hot_data = json.loads(utils.web.getUrl(f'{base_url}?order=max&limit=3'))

        if not hot_data:
            irc.error(_('No temperature data available'))
            return

        cold_region_data_list = []
        for region in _HOTNCOLD_REGIONS:
            try:
                cold_region_data_list.append(
                    json.loads(utils.web.getUrl(f'{base_url}?order=min&limit=3&regionCode={region}'))
                )
            except Exception:
                continue

        result = formatTemperatureExtremes(hot_data, cold_region_data_list)
        if result is None:
            irc.error(_('No cold temperature data available'))
            return

        irc.reply(result)

Class = Yr
