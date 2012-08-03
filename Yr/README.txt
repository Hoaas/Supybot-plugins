Yr.no is a service by the Norwegian Meterological Institute and the Norwegian Broadcasting Corporation (NRK).
This plugin was originally started as I have a weather station 200m away from where I live, and I do not have a thermometer. So I would check yr.no every time I wondered what the temperature was. This was also my first go at Python, so this is probably not the best way to do what this plugin does. The plugin have been expanded by popular demand, so it now accepts data for any location, as long as an URL to that location is added.

For Norwegian locations data from the closest weather station will be used. For other locations the forecast is used.

This plugin does NOT use the API.

It is Big and Ugly™. It "parses" HTML and will most likely break as soon as they change the HTML-code.

The URL for the location you are interested in must be located manually.

Supports all languages yr.no supports at this point.

Main feature is returning temperature, current weather, windspeed, windchill.

In addition sunrise/sunset, moonrise/moonset is available.

Also pollen forecast is available for Norway.

Examples (color coding and bold not included):
10:32:50 <@Hoaas> !temp
10:32:52 <@Bunisher> Add an URL for this alias first.

10:34:08 <@Hoaas> !location default http://www.yr.no/place/United_Kingdom/England/London/
10:34:08 <@Bunisher> Ok.
10:34:10 <@Hoaas> !temp
10:34:12 <@Bunisher> 18°. Cloudy. Gentle breeze, 5 m/s from south (Weather forecast for London, England (United Kingdom))
10:37:05 <@Hoaas> !sun
10:37:06 <@Bunisher> Sunrise 04:50. Sunset 21:19. (Weather forecast for London, England (United Kingdom))
10:37:09 <@Hoaas> !moon
10:37:11 <@Bunisher> Moonrise 20:46. Moonset 05:53. (Weather forecast for London, England (United Kingdom))


10:35:00 <@Hoaas> !location ny http://www.yr.no/place/United_States/New_York/New_York~5128581/
10:35:10 <@Hoaas> !temp ny
10:35:12 <@Bunisher> 21°. Rain. Light breeze, 2 m/s from southwest (Weather forecast for New York (United States))

10:35:13 <@Hoaas> !sun ny
10:35:15 <@Bunisher> Sunrise 05:30. Sunset 20:30. (Weather forecast for New York (United States))

10:35:24 <@Hoaas> !moon ny
10:35:26 <@Bunisher> Moonrise 20:16. Moonset 06:36. (Weather forecast for New York (United States))

10:41:21 <@Hoaas> !location mcmurdo http://www.yr.no/place/Antarctica/Other/McMurdo_Station/
10:41:21 <@Bunisher> Ok.
10:41:24 <@Hoaas> !temp mcmurdo
10:41:25 <@Bunisher> -32° (-39.8°). Partly cloudy. Light breeze, 2 m/s from south-southwest (Weather forecast for McMurdo Station (Antarctica))
10:41:48 <@Hoaas> !sun mcm
10:41:51 <@Bunisher> Polar night, the sun doesn’t rise. (Weather forecast for McMurdo Station (Antarctica))


(norwegian only, also only for Norway)
10:35:01 <@Hoaas> !pollen
10:35:04 <@Bunisher> Trøndelag: I dag: Gress (Beskjeden spredning). I morgen: Gress (Moderat spredning).

10:38:33 <@Hoaas> !pollen list
10:38:33 <@Bunisher> 1 Østlandet med Oslo, 2 Sørlandet, 3 Rogaland, 4 Hordaland, 5 Sogn og Fjordane, 6 Møre og Romsdal, 7 Sentrale fjellstrøk i Sør-Norge, 8 Indre Østlandet, 9 Trøndelag, 10 Nordland, 11 Troms, 12 Finnmark

10:38:53 <@Hoaas> !pollen møre
10:38:55 <@Bunisher> Møre og Romsdal: I dag: Gress (Beskjeden spredning). I morgen: Gress (Moderat spredning).

10:39:06 <@Hoaas> !pollen 1
10:39:08 <@Bunisher> Østlandet med Oslo: I dag: Gress (Moderat spredning). I morgen: Gress (Kraftig spredning).
