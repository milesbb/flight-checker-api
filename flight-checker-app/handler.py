import logging

import boto3
import os
import json
from typing import NamedTuple, Union


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class Location(NamedTuple):
    country: str | None
    city: str | None
    iata_code: str | None

    def __post_init__(self):
        # Validate field1 and field2 are either strings or None
        if not (self.country is None or isinstance(self.country, str)):
            raise TypeError(f"country must be a string or None, got {type(self.field1)}")
        if not (self.city is None or isinstance(self.city, str)):
            raise TypeError(f"city must be a string or None, got {type(self.field2)}")
        if (not (self.iata_code is None or isinstance(self.iata_code, str))):
            raise TypeError(f"iata_code must be a string or None, got {type(self.field2)}")
        if self.iata_code is not None and len(self.iata_code) != 3:
            raise TypeError(f"iata_code must be 3 letters long.")


class FlightCheckSettings(NamedTuple):
    home_airports: list[Location]
    specific_locations: list[Location]
    target_emails: str


def run_and_send_flight_check(settings: FlightCheckSettings):
    logger.info("NICE")

    body = 'test body'

    send_flight_check_data(
        recipient_emails=settings.target_emails,
        body=body
    )


def send_flight_check_data(recipient_emails: list[str], body: str):
    sender_email = 'milesbb101@gmail.com'
    subject = 'TEST_FLIGHT_CHECK_SUBJECT'

    send_email(
        sender_email=sender_email,
        recipient_emails=recipient_emails,
        subject=subject,
        body=body
    )


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
            home_airports=[Location(**home_airport) for home_airport in event["home_airports"]],
            specific_locations=[Location(**home_airport) for home_airport in event["specific_locations"]]
        )

        run_and_send_flight_check(settings=settings)
    except Exception as e:
        logger.error("Error occured", exc_info=True)
        raise e
    
    logger.info("Finished flight-checker function. Check your email :)")
