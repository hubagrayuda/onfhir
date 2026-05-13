from pydantic import BaseModel, ValidationError

from onfhir.core.types import UrlType


class UrlModel(BaseModel):
    val: UrlType


try:
    print(UrlModel(val="not a url"))
    print("DID NOT RAISE")
except ValidationError:
    print("RAISED")
