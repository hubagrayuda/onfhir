from pydantic import BaseModel, ValidationError

from onfhir.core.types import IntegerType


class IntegerModel(BaseModel):
    val: IntegerType


try:
    print(IntegerModel(val=2147483648))
    print("DID NOT RAISE")
except ValidationError as e:
    print("RAISED:", e)
