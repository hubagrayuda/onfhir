from pydantic import BaseModel, ValidationError

from onfhir.core.types import PositiveIntType, UnsignedIntType


class UM(BaseModel):
    val: UnsignedIntType


class PM(BaseModel):
    val: PositiveIntType


try:
    UM(val=-1)
    print("UM DID NOT RAISE")
except ValidationError:
    print("UM RAISED")

try:
    PM(val=0)
    print("PM DID NOT RAISE")
except ValidationError:
    print("PM RAISED")
