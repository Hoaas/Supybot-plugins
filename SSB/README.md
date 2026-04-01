This plugin uses ssb.no (Statistics Norway) to fetch statistics about Norwegian names.

## Commands

### `navn <name>`

Looks up how many Norwegians have a given name. Accepts first names, last names, or full names (first + last).

Results are grouped by name component and show the count and type. Gender is shown in parentheses for given names.

**Examples:**

```
!navn Terje
TERJE: 18994 first name (with middle name) (M), 15782 first name (only) (M)

!navn Hoås
HOÅS: 186 last name, 109 middle + last name

!navn Terje Hoås
HOÅS: 186 last name, 109 middle + last name | TERJE: 18994 first name (with middle name) (M), 15782 first name (only) (M)
```

## Configuration

### `supybot.plugins.SSB.language`

Override the output language. Leave empty to follow the global `supybot.language` setting.
Supported values: `en` (English, default), `no` (Norwegian).

```
config supybot.plugins.SSB.language no
```

Norwegian output example:

```
HOÅS: 186 etternavn, 109 mellomnavn og etternavn | TERJE: 18994 fornavn (med mellomnavn) (M), 15782 fornavn (kun) (M)
```
