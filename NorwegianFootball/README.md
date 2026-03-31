Fetches live match events and scores from the NIFS football API.

Data is sourced from Norway — match names and commentary are in Norwegian.

## Commands

### `fotball <team>`

Shows the latest score and most recent commentary for any active match whose
name contains the search term. Multiple matches are separated by ` | `.

The score reflects the current phase of the match: extra time and penalty
shootout scores are shown when applicable.

Example:

    <user> fotball Rosenborg
    <bot> Rosenborg - Molde 2 - 1 - Mål for Rosenborg! Keeper ble stående...
