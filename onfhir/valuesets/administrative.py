from enum import StrEnum


# -------------------
# Address
# -------------------
class AddressUse(StrEnum):
    HOME = "home"
    WORK = "work"
    TEMP = "temp"
    OLD = "old"
    BILLING = "billing"


class AddressType(StrEnum):
    POSTAL = "postal"
    PHYSICAL = "physical"
    BOTH = "both"


# -------------------
# ContactPoint
# -------------------
class ContactPointSystem(StrEnum):
    PHONE = "phone"
    FAX = "fax"
    EMAIL = "email"
    PAGER = "pager"
    URL = "url"
    SMS = "sms"
    OTHER = "other"


class ContactPointUse(StrEnum):
    HOME = "home"
    WORK = "work"
    TEMP = "temp"
    OLD = "old"
    MOBILE = "mobile"


# -------------------
# HumanName
# -------------------
class NameUse(StrEnum):
    USUAL = "usual"
    OFFICIAL = "official"
    TEMP = "temp"
    NICKNAME = "nickname"
    ANONYMOUS = "anonymous"
    OLD = "old"
    MAIDEN = "maiden"


# -------------------
# Identifier
# -------------------
class IdentifierUse(StrEnum):
    USUAL = "usual"
    OFFICIAL = "official"
    TEMP = "temp"
    SECONDARY = "secondary"
    OLD = "old"
