from decimal import Decimal

from app.schemas.insured import InsuredVerifyRequest, InsuredVerifyResponse


def verify_insured(payload: InsuredVerifyRequest, principal: dict) -> InsuredVerifyResponse:
    suffix = int(payload.id_card[-2:]) if payload.id_card[-2:].isdigit() else 0
    types = ["职工医保", "居民医保", "新农合"]
    statuses = ["在职", "退休", "居民医保"]
    return InsuredVerifyResponse(
        insured_id=f"INS{payload.id_card[-6:]}",
        status=statuses[suffix % len(statuses)],
        region="北京市",
        insurance_type=types[suffix % len(types)],
        account_balance=Decimal("2860.50") + Decimal(suffix),
    )
