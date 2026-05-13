from enum import StrEnum


# -------------------
# Quantity
# -------------------
class QuantityComparator(StrEnum):
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN_OR_EQUAL = ">="
    GREATER_THAN = ">"
