"""
Exception classes for esgf_consumer
"""


class ESGFConsumerException(Exception):
    """Base exception for all ESGF consumer exceptions"""


class ESGFConsumerUnknownPayloadError(ESGFConsumerException):
    """
    Raised when an unknown payload is received.

    An unknown payload is one that cannot be interpreted as a payload model from esgf_playground_utils
    """


class ESGFConsumerNotImplementedPayloadError(ESGFConsumerException):
    """
    Raised when a known payload which cannot yet be handled is received.
    """
