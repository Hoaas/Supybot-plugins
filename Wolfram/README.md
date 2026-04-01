Queries the [Wolfram Alpha](https://www.wolframalpha.com/) API and returns results in IRC.

Originally found online (believed to be written by Ed Summers), then modified by Terje Hoås. The original source could not be relocated.

## Commands

### `wolfram [--lines <num>] <query>`
### `alpha [--lines <num>] <query>`

Ask Wolfram Alpha a question. `alpha` is an alias for `wolfram`. "Input interpretation" pods are always skipped; up to `--lines` result pods are returned (default 2).

**Examples:**

```
!wolfram 5+5
Result: 10

!alpha distance Paris London
Result: 342 km (kilometers)

!wolfram --lines 1 population of Norway
Result: 5.549 million people (world rank: 119th) (2024 estimate)
```

## Configuration

### `supybot.plugins.Wolfram.apikey`

Your Wolfram Alpha API key. A free key can be obtained at https://developer.wolframalpha.com/.

```
config supybot.plugins.Wolfram.apikey <your key here>
```
