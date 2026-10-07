from decimal import Decimal

from pydantic import BaseModel, Field


class InsuredVerifyRequest(BaseModel):
    id_card: str = Field(min_length=15, max_length=18)
    medical_card_no: str = Field(min_length=6)


class InsuredVerifyResponse(BaseModel):
    insured_id: str
    status: str
    region: str
    insurance_type: str
    account_balance: Decimal
