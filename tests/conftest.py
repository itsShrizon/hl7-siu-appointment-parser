"""Pytest fixtures for HL7 parser tests."""
import pytest


@pytest.fixture
def valid_message() -> str:
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG001|P|2.5
SCH|12345|FILLER456||||Checkup^Routine|||||^^^20250502130000|||||||||||Room 101
PID|||P12345||Doe^John||19850210|M
PV1||O|CLINIC||||D001^Smith^Jane"""


@pytest.fixture
def empty_fields_message() -> str:
    """Message with empty fields (consecutive ||)."""
    return """MSH|^~\\&|APP|FAC|||20250502130000||SIU^S12|MSG002|P|2.5
SCH|||||||||||||||||||||Room 101
PID|||||||||
PV1||O"""


@pytest.fixture
def malformed_message() -> str:
    return """MSH|^~\\&|APP|FAC|||20250502130000||ADT^A01|MSG003|P|2.5
PID|||P999||Bad^Message"""
