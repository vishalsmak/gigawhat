import pytest

from gigawhat.assistant.pii import PiiMasker, pii_masker

pytestmark = pytest.mark.slow


@pytest.fixture(scope="module")
def masker() -> PiiMasker:
    return pii_masker()


def test_masks_a_customers_name(masker: PiiMasker) -> None:
    assert "Okafor" not in masker.mask("Mrs Janet Okafor says she can smell gas").text


def test_masks_house_number_and_street(masker: PiiMasker) -> None:
    assert masker.mask("smell outside 14 Station Road").text == "smell outside [address]"


def test_masks_address_written_with_number(masker: PiiMasker) -> None:
    assert "[address]" in masker.mask("outside number 22 Vale Road").text


def test_masks_postcode(masker: PiiMasker) -> None:
    assert "[postcode]" in masker.mask("the property at HR4 7QT").text


def test_masks_uk_mobile_number(masker: PiiMasker) -> None:
    assert "[phone]" in masker.mask("call her back on 07700 900123").text


def test_masks_landline_number(masker: PiiMasker) -> None:
    assert "[phone]" in masker.mask("on 01632 960 555 this morning").text


def test_masks_email_address(masker: PiiMasker) -> None:
    assert masker.mask("john.smith@example.com").text == "[email]"


def test_reports_entity_types_found(masker: PiiMasker) -> None:
    found = masker.mask("Janet Okafor, 14 Station Road").entities

    assert found == ("PERSON", "STREET_ADDRESS")


@pytest.mark.parametrize(
    "text",
    [
        "What is the outlet set point for G-112 at Mill Lane District Governor?",
        "Isolate the 11 kV feeder FDR-ASH-07 at Ashford Road Primary Substation",
        "Who is the Authorised Person for Kingsmead?",
        "Call the gas emergency line 0800 111 999",
        "Inspection INS-00412 on 2026-08-14 found 43.5 mbar; WO-00071 raised",
        "What does PR-GAS-031 say about the vent stack?",
        "G-112 logger max keeps coming up high overnight again",
    ],
)
def test_leaves_company_names_ids_and_readings_alone(masker: PiiMasker, text: str) -> None:
    assert masker.mask(text).text == text
