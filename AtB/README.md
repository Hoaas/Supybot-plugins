# AtB

Limnoria plugin for real-time bus information in Trondheim, Norway.

## Data source

Uses the NTNU bus oracle at `busstjener.idi.ntnu.no`, which provides
plain-text answers about bus departures in Trondheim based on a stop name
or a free-text question.

## Commands

### `buss <stop or question>`

Queries the NTNU bus oracle and returns the answer.

```
<Hoaas> !buss Berg
<bot>   Berg Bedehus mot sentrum: #75 om ca. 10 min.
```

## Configuration

No configuration required.
