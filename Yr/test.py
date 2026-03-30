###
# Copyright (c) 2010, Terje Hoaas
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
from datetime import datetime, timezone
from zoneinfo import ZoneInfoNotFoundError

import supybot.utils as utils
from supybot.test import *

from . import plugin as yr_plugin


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

def makeForecastData(temp=5.0, windspeed=3.0, winddirection=180.0,
                     humidity=70.0, rain=0.5, symbol='clearsky_day',
                     next1h=True):
    """Build a met.no forecast JSON payload as bytes."""
    data = {
        'properties': {
            'meta': {
                'units': {
                    'air_temperature': 'celsius',
                    'wind_speed': 'm/s',
                    'relative_humidity': '%',
                    'precipitation_amount': 'mm',
                },
            },
            'timeseries': [{
                'time': '2024-06-01T12:00:00Z',
                'data': {
                    'instant': {
                        'details': {
                            'air_temperature': temp,
                            'wind_speed': windspeed,
                            'wind_from_direction': winddirection,
                            'relative_humidity': humidity,
                        },
                    },
                    'next_1_hours': {
                        'summary': {'symbol_code': symbol},
                        'details': {'precipitation_amount': rain},
                    } if next1h else None,
                },
            }],
        },
    }
    return json.dumps(data).encode()


def makeGeonamesResponse(name='Oslo', adminName='Oslo', countryName='Norway',
                         lat='59.9133301', lng='10.7389701'):
    return json.dumps({
        'totalResultsCount': 1,
        'geonames': [{
            'toponymName': name,
            'adminName1': adminName,
            'countryName': countryName,
            'lat': lat,
            'lng': lng,
        }],
    }).encode()


def makeGeonamesEmpty():
    return json.dumps({'totalResultsCount': 0, 'geonames': []}).encode()


def makeSunriseResponse(sunrise='2024-06-01T04:32:00+02:00',
                        sunset='2024-06-01T22:14:00+02:00'):
    return json.dumps({
        'properties': {
            'sunrise': {'time': sunrise},
            'sunset': {'time': sunset},
        },
    }).encode()


def makeHotPlace(name, county, temp):
    return {'locationMetadata': {'name': name, 'county': county},
            'temperature': {'value': temp}}


# ---------------------------------------------------------------------------
# Unit tests for module-level helpers — no bot, no network
# ---------------------------------------------------------------------------

class YrHelperTestCase(SupyTestCase):

    # symbolToEmoji

    def testSymbolToEmojiClearsky(self):
        self.assertEqual(yr_plugin.symbolToEmoji('clearsky_day'), '☀')

    def testSymbolToEmojiClearskyNight(self):
        self.assertEqual(yr_plugin.symbolToEmoji('clearsky_night'), '☀')

    def testSymbolToEmojiFair(self):
        self.assertEqual(yr_plugin.symbolToEmoji('fair_day'), '🌤️')

    def testSymbolToEmojiPartlyCloudy(self):
        self.assertEqual(yr_plugin.symbolToEmoji('partlycloudy_day'), '🌤')

    def testSymbolToEmojiFog(self):
        self.assertEqual(yr_plugin.symbolToEmoji('fog'), '🌫️')

    def testSymbolToEmojiCloudy(self):
        self.assertEqual(yr_plugin.symbolToEmoji('cloudy'), '☁')

    def testSymbolToEmojiShowers(self):
        self.assertEqual(yr_plugin.symbolToEmoji('lightshowers_day'), '🌦️')

    def testSymbolToEmojiThunder(self):
        self.assertEqual(yr_plugin.symbolToEmoji('thunder'), '⛈️')

    def testSymbolToEmojiRain(self):
        self.assertEqual(yr_plugin.symbolToEmoji('heavyrain'), '🌧️')

    def testSymbolToEmojiSnow(self):
        self.assertEqual(yr_plugin.symbolToEmoji('heavysnow'), '🌨️')

    def testSymbolToEmojiSleet(self):
        self.assertEqual(yr_plugin.symbolToEmoji('lightsleet'), '🌨️🌧️')

    def testSymbolToEmojiUnknownReturnsSuffix(self):
        self.assertIn('.', yr_plugin.symbolToEmoji('unknown_code'))

    # windChill

    def testWindChillReturnsNoneWhenTempTooHigh(self):
        self.assertIsNone(yr_plugin.windChill(15, 10))

    def testWindChillReturnsNoneWhenWindTooLow(self):
        self.assertIsNone(yr_plugin.windChill(5, 1))

    def testWindChillReturnsValueForColdWindy(self):
        result = yr_plugin.windChill(0, 10)
        self.assertIsNotNone(result)
        self.assertLess(result, 0)

    # tempFormat

    def testTempFormatPositiveTemp(self):
        self.assertIn('5.0°', yr_plugin.tempFormat(5.0, None))

    def testTempFormatNegativeTemp(self):
        self.assertIn('-5.0°', yr_plugin.tempFormat(-5.0, None))

    def testTempFormatIncludesWindchill(self):
        self.assertIn('(', yr_plugin.tempFormat(0, 10))

    def testTempFormatNoWindchillWhenWarmOrCalm(self):
        self.assertNotIn('(', yr_plugin.tempFormat(15, 10))
        self.assertNotIn('(', yr_plugin.tempFormat(0, 0.5))

    # readTimeFromJson

    def testReadTimeFromJsonReturnsFormattedTime(self):
        j = {'properties': {'sunrise': {'time': '2024-06-01T04:32:00+02:00'}}}
        self.assertEqual(yr_plugin.readTimeFromJson(j, 'sunrise'), '04:32')

    def testReadTimeFromJsonMissingKeyReturnsQuestionMark(self):
        j = {'properties': {}}
        self.assertEqual(yr_plugin.readTimeFromJson(j, 'sunrise'), '❓')

    def testReadTimeFromJsonMissingTimeReturnsQuestionMark(self):
        j = {'properties': {'sunrise': {}}}
        self.assertEqual(yr_plugin.readTimeFromJson(j, 'sunrise'), '❓')

    # parseForecast

    def testParseForecastContainsTemperature(self):
        result = yr_plugin.parseForecast(makeForecastData(temp=7.0))
        self.assertIn('7.0°', result)

    def testParseForecastContainsWindspeed(self):
        result = yr_plugin.parseForecast(makeForecastData(windspeed=5.0))
        self.assertIn('5.0', result)

    def testParseForecastContainsHumidity(self):
        result = yr_plugin.parseForecast(makeForecastData(humidity=65.0))
        self.assertIn('65.0', result)

    def testParseForecastContainsRain(self):
        result = yr_plugin.parseForecast(makeForecastData(rain=1.2))
        self.assertIn('1.2', result)

    def testParseForecastContainsWindDirection(self):
        # 180 degrees = south
        result = yr_plugin.parseForecast(makeForecastData(winddirection=180.0))
        self.assertIn('south', result)

    def testParseForecastNorthWindDirection(self):
        result = yr_plugin.parseForecast(makeForecastData(winddirection=0.0))
        self.assertIn('north', result)

    def testParseForecastMissingNext1hReturnsErrorString(self):
        result = yr_plugin.parseForecast(makeForecastData(next1h=False))
        self.assertEqual(result, 'Weather data not available')

    def testParseForecastAcceptsBytesInput(self):
        data = makeForecastData(temp=3.0)
        self.assertIsInstance(data, bytes)
        self.assertIn('3.0°', yr_plugin.parseForecast(data))

    def testParseForecastAcceptsStringInput(self):
        data = makeForecastData(temp=3.0).decode()
        self.assertIsInstance(data, str)
        self.assertIn('3.0°', yr_plugin.parseForecast(data))

    # formatTemperatureExtremes

    def testFormatTemperatureExtremesHappyPath(self):
        hot = [makeHotPlace('Kautokeino', 'Finnmark', 28.0)]
        cold = [[makeHotPlace('Røros', 'Trøndelag', -15.0)]]
        result = yr_plugin.formatTemperatureExtremes(hot, cold)
        self.assertIn('Kautokeino', result)
        self.assertIn('Røros', result)

    def testFormatTemperatureExtremesEmptyHotReturnsNone(self):
        self.assertIsNone(yr_plugin.formatTemperatureExtremes([], []))

    def testFormatTemperatureExtremesEmptyColdReturnsNone(self):
        hot = [makeHotPlace('Kautokeino', 'Finnmark', 28.0)]
        self.assertIsNone(yr_plugin.formatTemperatureExtremes(hot, []))

    def testFormatTemperatureExtremesSortsColdByValue(self):
        hot = [makeHotPlace('Kautokeino', 'Finnmark', 28.0)]
        cold = [[
            makeHotPlace('Røros', 'Trøndelag', -10.0),
            makeHotPlace('Karasjok', 'Finnmark', -20.0),
            makeHotPlace('Folldal', 'Innlandet', -5.0),
        ]]
        result = yr_plugin.formatTemperatureExtremes(hot, cold)
        # Karasjok is coldest, should appear before Røros
        self.assertLess(result.index('Karasjok'), result.index('Røros'))

    # utcOffsetForTimezone

    def testUtcOffsetForTimezoneFormat(self):
        offset = yr_plugin.utcOffsetForTimezone('Europe/Oslo')
        import re
        self.assertRegex(offset, r'^[+-]\d{2}:\d{2}$')

    def testUtcOffsetForTimezoneOsloIsReasonable(self):
        offset = yr_plugin.utcOffsetForTimezone('Europe/Oslo')
        self.assertIn(offset, ('+01:00', '+02:00'))

    def testUtcOffsetForTimezoneUtc(self):
        self.assertEqual(yr_plugin.utcOffsetForTimezone('UTC'), '+00:00')

    def testUtcOffsetForTimezoneInvalidRaises(self):
        self.assertRaises(ZoneInfoNotFoundError,
                          yr_plugin.utcOffsetForTimezone, 'Not/ATimezone')


# ---------------------------------------------------------------------------
# Integration tests for bot commands — network calls are mocked
# ---------------------------------------------------------------------------

class YrCommandTestCase(PluginTestCase):
    plugins = ('Yr',)

    # temp command

    def testTempReturnsResult(self):
        def fakeGetUrl(url, **kw):
            if 'geonames' in url:
                return makeGeonamesResponse()
            return makeForecastData(temp=10.0)

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            self.assertNotError('temp #test Oslo')
        finally:
            utils.web.getUrl = original

    def testTempNotFound(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: makeGeonamesEmpty()
        try:
            self.assertError('temp #test Nonexistentplace')
        finally:
            utils.web.getUrl = original

    def testTempResponseContainsLocationInfo(self):
        def fakeGetUrl(url, **kw):
            if 'geonames' in url:
                return makeGeonamesResponse(name='Oslo', adminName='Oslo',
                                            countryName='Norway')
            return makeForecastData(temp=5.0)

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            self.assertRegexp('temp #test Oslo', r'Oslo.*Norway')
        finally:
            utils.web.getUrl = original

    # sun command

    def testSunReturnsResult(self):
        def fakeGetUrl(url, **kw):
            if 'geonames' in url:
                return makeGeonamesResponse()
            return makeSunriseResponse()

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            self.assertNotError('sun #test Oslo')
        finally:
            utils.web.getUrl = original

    def testSunNotFound(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: makeGeonamesEmpty()
        try:
            self.assertError('sun #test Nonexistentplace')
        finally:
            utils.web.getUrl = original

    def testSunResponseContainsTimes(self):
        def fakeGetUrl(url, **kw):
            if 'geonames' in url:
                return makeGeonamesResponse()
            return makeSunriseResponse(sunrise='2024-06-01T04:32:00+02:00',
                                       sunset='2024-06-01T22:14:00+02:00')

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            self.assertRegexp('sun #test Oslo', r'04:32')
            self.assertRegexp('sun #test Oslo', r'22:14')
        finally:
            utils.web.getUrl = original

    def testSunDefaultTimezoneShowsUtcLabel(self):
        def fakeGetUrl(url, **kw):
            if 'geonames' in url:
                return makeGeonamesResponse()
            return makeSunriseResponse()

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            # Default config is UTC — output should contain '(UTC)'
            self.assertRegexp('sun #test Oslo', r'\(UTC\)')
        finally:
            utils.web.getUrl = original

    def testSunInvalidTimezoneReturnsError(self):
        import supybot.conf as conf
        def fakeGetUrl(url, **kw):
            if 'geonames' in url:
                return makeGeonamesResponse()
            return makeSunriseResponse()

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            with conf.supybot.plugins.Yr.timezone.context('Not/ATimezone'):
                self.assertError('sun #test Oslo')
        finally:
            utils.web.getUrl = original

    # hotncold command

    def testHotncoldReturnsResult(self):
        hot = json.dumps([makeHotPlace('Kautokeino', 'Finnmark', 28.0)]).encode()
        cold = json.dumps([makeHotPlace('Røros', 'Trøndelag', -15.0)]).encode()

        def fakeGetUrl(url, **kw):
            if 'order=max' in url:
                return hot
            return cold

        original = utils.web.getUrl
        utils.web.getUrl = fakeGetUrl
        try:
            self.assertNotError('hotncold')
        finally:
            utils.web.getUrl = original

    def testHotncoldNoHotDataReturnsError(self):
        original = utils.web.getUrl
        utils.web.getUrl = lambda url, **kw: b'[]'
        try:
            self.assertError('hotncold')
        finally:
            utils.web.getUrl = original
