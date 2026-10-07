# gbinsureapi 医保智能结算 API 网关

```bash
cp .env.example .env
docker compose up -d --build
curl http://localhost:19935/health
```

gbinsureapi 为医院信息系统提供标准化医保结算接口，覆盖身份核验、费用上传、预结算、正式结算、冲正、查询和日终对账。

## 主要功能

- 参保人身份核验：基于身份证号和医保卡号返回参保状态、参保地、医保类型和账户余额。
- 费用明细上传：校验药品、诊疗、耗材、检查明细，生成上传批次号并做重复检查。
- 预结算计算：按医保目录类别（甲/乙/丙）和参保地政策返回报销基数、医保报销、个人账户支付、自费金额等分项。
- 正式结算与冲正：服务端按统一口径重算后生成结算单号，支持当日全额回退。
- 结算单查询与对账：按结算单号、参保人和日期范围查询，日终汇总按同一口径分项统计。
- API 文档与权限：Swagger UI、API Key + JWT 双重认证、调用审计日志。

## 结算口径（预结算 / 正式结算 / 查询 / 对账统一）

- **甲类**：整条明细金额计入报销基数，无目录自付。
- **乙类**：**以明细上填写的自付比例为准**（`class_b_basis = ITEM_SELF_PAY_RATIO`）——先按 `金额 × 自付比例` 扣除先行自付，剩余金额计入报销基数。
- **丙类**：整条算自费，不计入报销基数。
- **乙类口径选择**：乙类同时存在目录固定比例和明细自付比例两种口径，本网关确定采用**明细自付比例优先**。若改用目录固定比例（乙类视同甲类整条进基数），同一张单的报销金额更高、自费更低；两种口径结果不同，为与医保局对账一致，全链路固定为明细自付比例口径，并在预结算返回的 `class_b_basis` / `class_b_basis_desc` 中明确标注。
- **报销计算**：`可报金额 = 报销基数 − 起付线`，再乘以报销比例 0.78；参保地以“市”结尾起付线 650，否则 450。**报销基数不足起付线时医保报销记 0**（`below_deductible=true`），起付线计入个人负担。
- **个人账户支付**：`个人账户支付 = min(账户余额, 个人负担总额)`，即既不超过账户余额，也不超过自费（个人负担）总额；余额通过身份核验获取并随预结算请求 `account_balance` 传入，不传时按兜底 800.00 计算。
- **勾稽关系**：`总费用 = 医保报销 + 个人账户支付 + 个人自费`，所有金额保留两位小数。
- 正式结算不信任调用方回传的金额，服务端用同一 `calculate_settlement` 重算后落库，避免回传金额与网关/医保局口径不一致。

预结算返回新增分类与口径字段：`class_a_amount`、`class_b_amount`、`class_b_self_pay_amount`、`class_c_self_pay_amount`、`reimbursement_base`、`below_deductible`、`account_balance`、`class_b_basis`、`class_b_basis_desc`；明细项返回每条的 `catalog_self_pay_amount`（目录自付）和 `eligible_amount`（计入报销基数金额）。日终对账在原汇总基础上增加 `total_reimbursed_amount`、`total_account_pay_amount`、`total_self_pay_amount`、`reversed_count`。

## 访问地址

- 健康检查：<http://localhost:19935/health>
- Swagger 文档：<http://localhost:19935/docs>

## API 调用示例

```bash
TOKEN=$(curl -s -X POST http://localhost:19935/api/auth/token \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-api-key" \
  -d '{"client_id":"his-demo","scopes":["settlement:write","settlement:read"]}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

curl -s http://localhost:19935/api/insured/verify \
  -H "Content-Type: application/json" \
  -H "X-API-Key: demo-api-key" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"id_card":"110101199001010012","medical_card_no":"YB00010001"}'
```

## 技术栈

| 分类 | 技术 |
| --- | --- |
| 后端框架 | FastAPI + Python 3.11 |
| 数据库 | PostgreSQL |
| ORM | SQLAlchemy |
| 迁移 | Alembic 目录预留 |
| 校验 | Pydantic |
| 认证 | API Key + JWT |
| 文档 | Swagger UI / OpenAPI |

## 目录结构

```text
.
├── docker-compose.yml
├── .env.example
├── README.md
├── backend
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app
│       ├── api
│       ├── core
│       ├── db
│       ├── models
│       ├── schemas
│       └── services
└── database
    └── init.sql
```

## 环境变量

| 变量 | 说明 |
| --- | --- |
| COMPOSE_PROJECT_NAME | Docker Compose 项目名 |
| DB_NAME / DB_USER / DB_PASSWORD | PostgreSQL 数据库配置 |
| JWT_SECRET | JWT 签名密钥 |
| API_KEY_SECRET | API Key 校验密钥 |
| BACKEND_PORT | 后端宿主机端口，默认 19935 |

## 本地开发

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 19935
```

## License

MIT
