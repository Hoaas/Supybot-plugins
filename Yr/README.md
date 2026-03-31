# Yr

A [Limnoria](https://github.com/ProgVal/Limnoria) IRC bot plugin that fetches
weather information from the [met.no](https://api.met.no) and
[yr.no](https://www.yr.no) APIs.

## Data sources

- **Weather forecasts**: [met.no API](https://api.met.no) — nowcast (Nordic
  area) with fallback to locationforecast for global coverage
- **Location search**: [GeoNames](https://www.geonames.org) — resolves city
  names to coordinates
- **Sunrise/sunset**: met.no sunrise API
- **Temperature extremes**: yr.no moduler API (Norway only)

## Commands

### `temp <city>`

Looks up the city on GeoNames and fetches the current weather forecast from
met.no. Reports temperature, weather symbol, wind speed and direction,
humidity, and precipitation.

```
<you> temp Oslo
<bot> 🌤 12° Wind 4 m/s from southwest. 65% humidity. (Oslo, Oslo, Norway)
```

### `sun <city>`

Shows sunrise and sunset times for the given city.

```
<you> sun Oslo
<bot> ☀⬆ 05:12 ☀⬇ 21:44 (UTC), (Oslo, Oslo, Norway)
```

The timezone used to display times is controlled by the `timezone` config var
(see below).

### `hotncold`

Lists the 3 hottest and 3 coldest places in Norway at the current hour.

```
<you> hotncold
<bot> 🔥 Hottest: Kautokeino (Finnmark) 28° | 🧊 Coldest: Røros (Trøndelag) -3°
```

This command only covers Norway (data source is Norway-only).

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `supybot.plugins.Yr.timezone` | `UTC` | Timezone for displaying sunrise/sunset times. Must be a valid tz database name (e.g. `Europe/Oslo`). When set to `UTC`, times are shown with a `(UTC)` label. |
| `supybot.plugins.Yr.language` | *(empty)* | Override the display language for this plugin. Leave empty to follow the global `supybot.language`. Accepts any locale code with a matching `.po` file, e.g. `no` for Norwegian. |

To set the timezone for a channel and enable Norwegian output:

```
config channel #yourchannel supybot.plugins.Yr.timezone Europe/Oslo
config supybot.plugins.Yr.language no
```

## Installation

```bash
pip install "limnoria-yr @ git+https://github.com/Hoaas/Supybot-plugins.git#subdirectory=Yr"
```

Or from a local clone:

```bash
pip install ./Yr/
```
