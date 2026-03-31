# Badetemperatur

A [Limnoria](https://github.com/ProgVal/Limnoria) IRC bot plugin that shows
bathing water temperatures for locations in Norway.

## Data source

Data is fetched from the [Yr.no](https://www.yr.no) public API
(`/api/v0/regions/NO/watertemperatures`). **The data source only covers
Norway** — searches for locations outside Norway will return no results.
Entries older than 7 days are automatically excluded.

## Commands

### `badetemp <location>`

Searches for bathing sites whose region name contains `<location>`
(case-insensitive) and reports the current water temperature for each match.

```
<you> badetemp Oslo
<bot> 19.2° Sollerudstranda, 18.8° Tjuvholmen, 19.0° Ingierstrand
```

Multiple results are returned comma-separated. If no matching locations are
found, an error message is shown.

## Configuration

| Key | Default | Description |
|-----|---------|-------------|
| `supybot.plugins.Badetemperatur.language` | *(empty)* | Override the display language for this plugin. Leave empty to follow the global `supybot.language`. Accepts any locale code with a matching `.po` file, e.g. `no` for Norwegian. |

To enable Norwegian output:

```
config supybot.plugins.Badetemperatur.language no
```

## Installation

```bash
pip install "limnoria-badetemperatur @ git+https://github.com/Hoaas/Supybot-plugins.git#subdirectory=Badetemperatur"
```

Or from a local clone:

```bash
pip install ./Badetemperatur/
```
