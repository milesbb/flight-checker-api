"""Very light weight script to get flight data and send it to emails"""

import logging

import boto3
import os
import json
import requests
from datetime import datetime
from typing import NamedTuple, Union


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

FLIGHTS_API_URL = os.getenv("FLIGHTS_SCRAPER_HOST_URL")
FLIGHTS_API_KEY = os.getenv("FLIGHTS_SCRAPER_API_KEY")


REQUEST_HEADERS = {
    "x-rapidapi-key": FLIGHTS_API_KEY,
    "x-rapidapi-host": FLIGHTS_API_URL
}


DEFAULT_REQ_PARAMS = {
    "currency": "GBP",
    "locale": "en-GB",
    "market": "UK"
}

SEARCH_EVERYWHERE = "search-everywhere"
SEARCH_ROUNDTRIP = 'search-roundtrip'

# In GBP
EVERYWHERE_PRICE_LIMIT = 50
ROUNDTRIP_PRICE_LIMIT = 130

current_datetime = datetime.now()


class Location(NamedTuple):
    country: str | None
    city: str | None
    iata_code: str | None

    def __post_init__(self):
        # Validate field1 and field2 are either strings or None
        if not (self.country is None or isinstance(self.country, str)):
            raise TypeError(
                f"country must be a string or None, got {type(self.field1)}")
        if not (self.city is None or isinstance(self.city, str)):
            raise TypeError(
                f"city must be a string or None, got {type(self.field2)}")
        if (not (self.iata_code is None or isinstance(self.iata_code, str))):
            raise TypeError(
                f"iata_code must be a string or None, got {type(self.field2)}")
        if self.iata_code is not None and len(self.iata_code) != 3:
            raise TypeError(f"iata_code must be 3 letters long.")


class FlightCheckSettings(NamedTuple):
    home_airports: list[Location]
    specific_locations: list[Location]
    target_emails: str


class RoundTrip(NamedTuple):
    origin: str
    destination: str
    price: str
    stops: int


class PotentialDestination(NamedTuple):
    destination: str
    cheapest_price: str
    is_cheapeast_direct: bool
    cheapest_direct: str


class FlightCheckData(NamedTuple):
    search_everywhere: list[PotentialDestination]
    specific_roundtrips: dict[str, dict[str, list[RoundTrip]]]


def make_request(params: dict, req_path: str):
    full_request_path = f"{FLIGHTS_API_URL}/flights/{req_path}"

    logger.info(
        f"Making request with url {full_request_path} and parameters {params}")

    response = requests.get(
        url=full_request_path, headers=REQUEST_HEADERS, params=params)

    print(response)
    print(response.reason)
    print(response.status_code)

    data = response.json()

    if response.status_code != 200:
        raise Exception(f'Error with the request: {data["message"]}')
    else:
        return data


def get_prices(journey: dict) -> dict:
    return journey['content']['flightQuotes']


def search_everywhere(main_home_airport: Location) -> list[PotentialDestination]:
    logger.info(f"Running search everywhere for {main_home_airport.city}")

    search_everywhere_params = {
        **DEFAULT_REQ_PARAMS,
        "fromEntityId": main_home_airport.iata_code,
        "type": 'roundtrip',
        "year": current_datetime.year,
        "month": current_datetime.month + 2
    }

    search_everywhere_data = make_request(
        params=search_everywhere_params, req_path=SEARCH_EVERYWHERE
    )

    logger.info("Finished search everywhere request")

    possible_journeys = search_everywhere_data['data']['everywhereDestination']['results']

    if len(possible_journeys) > 0:
        # under 50 squid
        cheapish_journeys = [PotentialDestination(
            destination=journey['content']['location']['name'],
            cheapest_price=get_prices(journey)['cheapest']['price'],
            is_cheapeast_direct=get_prices(journey)['cheapest']['direct'],
            cheapest_direct=get_prices(journey)['direct']['price'],
        ) for journey in possible_journeys if int(get_prices(journey)['cheapest']['price'].replace("£", "")) < EVERYWHERE_PRICE_LIMIT]

        return cheapish_journeys
    else:
        return []


def specific_roundtrip(from_location: Location, to_location: Location) -> list[PotentialDestination]:
    logger.info(
        f"Running specific roundtrip search for {from_location.city} to {to_location.city}")
    search_roundtrip_route = {
        **DEFAULT_REQ_PARAMS,
        "fromEntityId": from_location.iata_code,
        "type": 'roundtrip',
        "year": str(current_datetime.year),
        "month": str(current_datetime.month + 2)
    }

    roundtrip_data = make_request(
        params=search_roundtrip_route,
        req_path=SEARCH_ROUNDTRIP
    )

    itineraries = roundtrip_data['data']['itineraries']
    # under 130 squid
    roundtrips = [
        RoundTrip(
            origin=roundtrip['legs'][0]['origin']['name'],
            destination=roundtrip['legs'][0]['destination']['name'],
            price=roundtrip['price']['formatted'],
            stops=roundtrip['stopCount']
        ) for roundtrip in itineraries if roundtrip['price']['raw'] < ROUNDTRIP_PRICE_LIMIT
    ]

    logger.info('Finished roundtrip search')
    return roundtrips


def get_flights_data(settings: FlightCheckSettings) -> FlightCheckData:
    cheapish_journeys_from_main_airport = search_everywhere(
        main_home_airport=settings.home_airports[0]
    )

    data = {
        "search_everywhere": cheapish_journeys_from_main_airport,
        "specific_roundtrips": {}
    }

    for from_location in settings.home_airports:
        for target_location in settings.specific_locations:
            data["specific_roundtrips"][from_location.city][target_location.city] = specific_roundtrip(
                from_location=from_location,
                to_location=target_location
            )
    return FlightCheckData(
        search_everywhere=data['search_everywhere'],
        specific_roundtrips=data['specific_roundtrips']
    )


def generate_bullet_list(items, bullet="•") -> str:
    return "\n".join(f"{bullet} {item}" for item in items)


def generate_flight_check_summary(data: FlightCheckData) -> str:
    logger.info('Creating summary')
    summary = f"Today's flight prices:\n\nHome airport flights under {str(EVERYWHERE_PRICE_LIMIT)} quid:\n\n"
    summary += generate_bullet_list(
        [
            f"Flight to {journey.destination} for {journey.cheapest_price}.{'' if journey.is_cheapeast_direct else f' Cheapest direct flight: {journey.cheapest_direct}'}"
            for journey in data.search_everywhere
        ]
    )
    for origin, destination_roundtrips in data.specific_roundtrips.items():
        for destination, roundtrips in destination_roundtrips.items():
            summary += f"\n\nRound trips for {origin} -> {destination} in 2 months\n"
            summary += generate_bullet_list(
                [
                    f"Round trip from {roundtrip.origin} to {roundtrip.destination} for {roundtrip.price} with {roundtrip.stops} stops."
                    for roundtrip in roundtrips
                ]
            )

    summary += '\n\nStay tuned for more flight updates every Monday and Friday at 6pm!'

    logger.info('Finished summary')
    return summary


def run_and_send_flight_check(settings: FlightCheckSettings):
    logger.info("Running flight check")

    data = get_flights_data(settings)

    summary = generate_flight_check_summary(settings)

    send_flight_check_data(
        recipient_emails=settings.target_emails,
        body=summary
    )


def send_flight_check_data(recipient_emails: list[str], body: str):
    sender_email = 'milesbb101@gmail.com'
    subject = 'CarrGaard Flight Prices Summary'

    logger.info('Sending summary:')
    logger.info(body)

    print(body)

    send_email(
        sender_email=sender_email,
        recipient_emails=recipient_emails,
        subject=subject,
        body=body
    )

    logger.info('Email(s) sent')


def send_email(
    sender_email: str,
    recipient_emails: list[str],
    subject: str,
    body: str
):
    ses_client = boto3.client('ses', region_name="eu-west-2")

    response = ses_client.send_email(
        Source=sender_email,
        Destination={
            'ToAddresses': recipient_emails
        },
        Message={
            'Subject': {'Data': subject},
            'Body': {'Text': {'Data': body}}
        }
    )


def handler(event, context):
    logger.info("flight-checker function invoked")

    try:
        logger.info(f"Event: {event}")

        settings = FlightCheckSettings(
            target_emails=event["target_emails"],
            home_airports=[Location(**home_airport)
                           for home_airport in event["home_airports"]],
            specific_locations=[Location(**home_airport)
                                for home_airport in event["specific_locations"]]
        )

        run_and_send_flight_check(settings=settings)
    except Exception as e:
        logger.error("Error occured", exc_info=True)
        raise e

    logger.info("Finished flight-checker function. Check your email :)")
