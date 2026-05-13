from pydantic import BaseModel

from onfhir.core.types import IntegerType


class IM(BaseModel):
    val: IntegerType = None


IM(val=2147483648)
