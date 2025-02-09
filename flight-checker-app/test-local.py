from handler import handler

handler(event={
    "target_emails": [
        "milesbb101@gmail.com"
    ],
    "home_airports": [
        {
            "country": "United Kingdom",
            "city": "Bristol",
            "iata_code": "BRS"
        }
    ],
    "specific_locations": [
        {
            "country": "Denmark",
            "city": "Aalborg",
            "iata_code": "AAL"
        },
        {
            "country": "Denmark",
            "city": "Copenhagen",
            "iata_code": "CPH"
        }
    ]
}, context={})
