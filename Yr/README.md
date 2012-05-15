Yr.no
-----

Yr.no is a service by the Norwegian Meterological Institute and the Norwegian Broadcasting Corporation (NRK).

This plugin was originally started as I have a weather station 200m away from where I live, 
and I do not have a thermometer. So I would check yr.no every time I wondered what the temperature was.

This was also my first go at Python, so this is probably not the best way to do what this plugin does.
The plugin have been expanded by popular demand, so it now accepts data for any location, as long as 
an URL to that location is added.

For Norwegian locations data from the closest weather station will be used. For other locations 
the forecast is used.

This plugin does NOT use the API.

It is Big and Ugly™. It "parses" HTML and will most likely break as soon as they change the HTML-code.

The URL for the location you are interested in must be located manually.

Supports all languages yr.no supports at this point.

Main feature is returning temperature, current weather, windspeed, windchill.

In addition sunrise/sunset, moonrise/moonset is available.

Also pollen forecast is available for Norway.
