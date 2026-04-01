# GodtNo

A [Limnoria](https://github.com/ProgVal/Limnoria) IRC bot plugin that fetches
a random dinner recipe from [godt.no](https://www.godt.no).

## Data source

Data is fetched from the godt.no internal GraphQL API. **The data source is
Norwegian only** — all recipe titles and links are in Norwegian.

## Commands

### `middag`

Returns a random published dinner recipe, including its title, cooking time,
and a direct link to the recipe page.

```
<you> middag
<bot> Pasta Carbonara (25 minutter) - https://godt.no/oppskrifter/pasta-carbonara
```

If no cooking time is available for the recipe, it is omitted from the output.

## Installation

```bash
pip install "limnoria-godtno @ git+https://github.com/Hoaas/Supybot-plugins.git#subdirectory=GodtNo"
```

Or from a local clone:

```bash
pip install ./GodtNo/
```
