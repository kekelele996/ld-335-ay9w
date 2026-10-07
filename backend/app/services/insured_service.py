from decimal import Decimal

from app.schemas.insured import InsuredVerifyRequest, InsuredVerifyResponse


def get_account_balance(insured_id: str) -> Decimal:
    """按参保号返回模拟个人账户余额，口径与身份核验接口一致。"""
    tail = insured_id[-2:]
    suffix = int(tail) if tail.isdigit() else 0
    return Decimal("2860.50") + Decimal(suffix)


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
