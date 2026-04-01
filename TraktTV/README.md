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
When registering, add `urn:ietf:wg:oauth:2.0:oob` as a redirect URI to enable device authentication.

```
/msg bot config supybot.plugins.TraktTV.client_id    YOUR_CLIENT_ID
/msg bot config supybot.plugins.TraktTV.client_secret YOUR_CLIENT_SECRET
```

### Why both credentials are needed

The `client_id` is required for every API call (sent as the `trakt-api-key` header).

The `client_secret` is **not** needed for regular read-only API calls or for `np` on
public profiles. However, it is required for any OAuth token operation — specifically
for exchanging an authorization code for an access token, and for **refreshing** that
token when it expires. Since March 2025, Trakt access tokens expire after **24 hours**,
so the bot will need to refresh the token daily using `/oauth/token`. If the secret is
not configured, token renewal will silently fail and authenticated requests (e.g. `np`
on private profiles) will stop working.

Configure both credentials upfront to avoid disruption.

## OAuth (for private profiles / `np`)

The `np` command can access private Trakt.tv profiles if you authenticate the bot
via the device-flow OAuth process. Run `auth` in a private message to the bot; it will
print a URL and a code. Visit the URL, enter the code, and the bot will store
the access token locally. Use `clearauth` to clear the stored token and re-authenticate.
