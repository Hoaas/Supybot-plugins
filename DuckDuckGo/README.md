# DuckDuckGo

Returns instant answers from the [DuckDuckGo Zero-Click Info API](https://duckduckgo.com/api).

Supports DuckDuckGo's instant answer types: abstracts (usually from Wikipedia
or other reference sources), direct answers (calculations, conversions,
random choices), definitions, and related results. Returns at most 3 replies
per query to avoid spam.

For full details on what DuckDuckGo's instant answers support, see:
- https://duckduckgo.com/bang.html
- https://duckduckgo.com/goodies.html
- https://duckduckgo.com/tech.html

Note: bang redirects (`!g`, `!gm`, etc.) and WolframAlpha results are not
available through the Zero-Click API.

## Commands

### `ddg <query>`

Searches DuckDuckGo and returns any Zero-Click information available.

```
<Hoaas> !ddg Audi A4
<Bot> The Audi A4 is a line of compact executive cars produced since late 1994 by the German car manufacturer Audi, a subsidiary of the Volkswagen Group. (Wikipedia)

<Hoaas> !ddg Keldar
<Bot> Keldar was a Ferengi, the husband of Ishka and the father of Quark and Rom. (Memory Alpha)

<Hoaas> !ddg pizza or burger or salad
<Bot> salad

<Hoaas> !ddg flip this
<Bot> sıɥʇ

<Hoaas> !ddg square root of nine
<Bot> The 2-root of 9 is 3 3 times the 2-root of 1.

<Hoaas> !ddg average 12 45 87
<Bot> Mean: 48; Median: 45; Root Mean Square: 56.9736781329765
```

## Installation

```bash
pip install ./DuckDuckGo/
```

Then load the plugin in your Limnoria bot:

```
/msg bot load DuckDuckGo
```
