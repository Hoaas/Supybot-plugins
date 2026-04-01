Shows the currently playing or last played track for a Last.fm user.

## Setup

Obtain a Last.fm API key at https://www.last.fm/api/account and configure it:

```
config supybot.plugins.LastFM.apikey <your-api-key>
```

## Commands

- `lastfm [--notags] [user]` — Show last/now-playing track for a user (defaults to caller's nick).
- `add <username> [nick]` — Link a nick to a Last.fm username.
- `whosplaying [--allatonce] [--skipplays]` — Show what everyone in the channel is playing.

## Example

```
<Hoaas> !lastfm
<bot> Hoaas np. Miike Snow - Animal [3 plays] [3:48] [indie pop, electropop]

<Hoaas> !lastfm somenick
<bot> somenick last played Radiohead - Creep [5 plays] [3:58] [alternative rock] (2 days ago)
```
