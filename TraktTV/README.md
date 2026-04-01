# TraktTV

Limnoria plugin for the [Trakt.tv](https://trakt.tv) API.

## Features

- **`np [nick]`** — Show what a Trakt.tv user is currently watching (requires public profile or OAuth).
- **`trending <movies|shows>`** — Top 10 trending movies or shows.
- **`popular <movies|shows>`** — Top 10 popular movies or shows.
- **`played <movies|shows> [daily|weekly|monthly|yearly]`** — Top 10 most played.
- **`watched <movies|shows> [daily|weekly|monthly|yearly]`** — Top 10 most watched.
- **`collected <movies|shows> [daily|weekly|monthly|yearly]`** — Top 10 most collected.
- **`anticipated <movies|shows>`** — Top 10 most anticipated.
- **`rating <movie|show> <name>`** — Rating and vote distribution for a title.
- **`random <show>`** — Pick a random episode from a show.

## Configuration

Obtain API credentials from <https://trakt.tv/oauth/applications> by creating a new application.

```
/msg bot config supybot.plugins.TraktTV.client_id    YOUR_CLIENT_ID
/msg bot config supybot.plugins.TraktTV.client_secret YOUR_CLIENT_SECRET
```

## OAuth (for private profiles / `np`)

The `np` command can access private Trakt.tv profiles if you authenticate the bot
via the device-flow OAuth process. Run `np` without arguments once; the bot will
print a URL and a code. Visit the URL, enter the code, and the bot will store
the access token locally.
