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
- 预结算计算：按医保目录（甲/乙/丙类）和参保地政策返回医保报销、个人账户支付、自费金额等分项。
- 正式结算与冲正：生成结算单号，支持当日全额回退。
- 结算单查询与对账：按结算单号、参保人和日期范围查询，提供日终汇总。
- API 文档与权限：Swagger UI、API Key + JWT 双重认证、调用审计日志。

## 结算口径

预结算、正式结算、结算单查询和日终对账使用同一套计算口径：

- **甲类**：整条明细金额纳入报销基数。
- **乙类**：先按自付比例扣除先行自付部分，剩余金额进基数。自付比例**以费用明细填写为准**；明细未填写时按目录默认比例（乙类 10%）计算。每条明细实际采用的比例和来源（明细自付比例 / 目录默认比例 / 类别规则）在预结算返回的 `item_breakdowns` 中逐条列明，整体口径见返回的 `ratio_rule` 字段。
- **丙类**：整条全额自费，不进报销基数。
- **起付线**：报销基数不足起付线时，医保报销记零；超过后按（基数 − 起付线）× 报销比例计算。
- **个人账户支付**：不超过账户余额，也不超过需个人承担的总额（总费用 − 医保报销），超出部分计入自费。
- 正式结算按费用明细重新计算后落库，不直接采用调用方传入的预结算金额，保证与预结算口径一致。

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
