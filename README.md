# Flight Checker Script

Script using AWS Lambda, Event Bridge, and SES for checking flights and coming up with a summary.

Helps me not miss the unicorn <£20 flights via semi-weekly flight updates.

## Example event data

```json
{
  "target_emails": ["example@example.com"],
  "home_airports": [
    // Including multiple will automatically search for each permutation of home airport and 'specific_locations' entry
    // The first home airport will also have a general search for cheap flights anywhere
    { "country": "United Kingdom", "city": "Bristol", "iata_code": "BRS" },
    { "country": "United Kingdom", "city": "London", "iata_code": "LHR" }
  ],
  "specific_locations": [
    // Search specific cities
    { "country": "Denmark", "city": "Copenhagen", "iata_code": "CPH" }
  ]
}
```
