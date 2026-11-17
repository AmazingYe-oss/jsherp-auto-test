# jshERP 自动化测试练习（API + UI）

基于开源管伊佳（jshERP）本地 Docker 环境写的一套接口和 UI 自动化测试，用来练习用例设计、接口测试、数据库落库核对和缺陷记录。

目前包含 **11 条接口用例** 和 **5 条 UI 用例**：
- 接口测试：登录鉴权（含无 token、错 token、登出失效）、商品增删改查、异常输入与多明细事务回滚、采购入库与删单冲销（加 MySQL 库存对账）
- UI 测试：Playwright 登录、商品名称/单位必填提示、新增查询与编辑规格

## 目录说明

- `tests/test_interface_login.py`：登录与商品列表查询
- `tests/test_interface_material.py`：商品新增、查询与清理
- `tests/test_interface_auth.py`：未登录、无效 token、主动登出失效拦截
- `tests/test_interface_material_negative.py`：重复条码、超长字段、多明细第 2 条冲突回滚
- `tests/test_interface_purchase_flow.py`：供应商 → 商品 → 采购入库 → 删单冲销（接口 + MySQL 双重校验）
- `tests/test_login.py` / `tests/test_material_validation.py`：Playwright UI 用例
- `conftest.py`：读取 `.env` 配置、接口登录、自动清理商品 `material_cleaner`、MySQL 连接 `db_conn`
- `material_add_cases.xlsx`：新增商品 20 条测试用例（等价类、边界值、组合、错误推测）
- `API_TRACEABILITY.md`：用例编号和脚本对应关系
- `API_REFERENCE.md`：整理过的接口地址、请求参数和表结构备忘
- `BUGS.md`：测试过程中发现并验证的问题记录（`ERP-001` ~ `ERP-004`）
- `.github/workflows/api-tests.yml`：CI 检查（依赖安装、Python 编译与用例收集）

## 环境配置与运行

需要本地先起好 jshERP 服务（默认 `http://127.0.0.1:18090`），Python 3.12+ 环境：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

编辑 `.env`，填好账号密码和本地测试库 `DB_*` 连接信息（密码和 token 不会写进代码或文档）。

运行全量接口测试并生成 Allure 报告：

```bash
pytest -v \
  tests/test_interface_login.py \
  tests/test_interface_material.py \
  tests/test_interface_auth.py \
  tests/test_interface_material_negative.py \
  tests/test_interface_purchase_flow.py \
  --alluredir=reports/allure-results --clean-alluredir

allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
```

运行 Playwright UI 测试（需要先 `python -m playwright install chromium`）：

```bash
pytest -v tests/test_login.py tests/test_material_validation.py
```

## 踩坑与实现细节

1. **同秒频控清会话（`ERP-001`）**：jshERP 后端在同一秒内连续操作会清除登录 session，导致后续接口报错 500，所以写/删请求中间统一留了 `time.sleep(2)`。
2. **MySQL 查询隔离级别**：`db_conn` 开启了 `autocommit=True`，否则同一个长连接里查不到接口刚刚写进库的新数据。
3. **业务流清理顺序**：入库单关联着商品和供应商，不先删入库单直接删商品会被后端拦截。因此 `finally` 里先删入库单、再删供应商，最后由 `material_cleaner` fixture 删商品，保证用例报错也能清理。
4. **已知限制**：被测 jshERP 跑在本地 Docker 容器里，GitHub Actions 云端跑不通本地端口，所以 CI 目前只跑语法检查和 `pytest --collect-only` 用例收集；接口也只覆盖了商品、鉴权和采购入库主流程，没有覆盖全系统三百多个接口。
