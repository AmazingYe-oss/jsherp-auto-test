# jshERP 自动化测试实战项目（接口 + UI + DB 双重断言）

基于本地 Docker 部署的开源管伊佳（jshERP）系统，使用 **Python + pytest + requests + PyMySQL + Playwright + Allure** 完成的接口与 UI 自动化测试项目。项目严格遵循“**灰盒约束分析 → 用例设计先行 → 自动化脚本编号追溯 → 接口与数据库双重断言 → 缺陷闭环**”的工程流程。

---

## 一、核心工程成果

1. **接口自动化测试集（11 条核心用例）**：
   - **认证与只读查询**（[tests/test_interface_login.py](tests/test_interface_login.py)）：MD5 小写加密登录、商品分页列表结构与数据类型断言；
   - **商品增删改查闭环**（[tests/test_interface_material.py](tests/test_interface_material.py)）：新增 → 精确查询 → `material_cleaner` 自动清理并复查 0 残留；
   - **鉴权安全边界**（[tests/test_interface_auth.py](tests/test_interface_auth.py)）：无 token / 无效 token / 主动 `/user/logout` 失效 token 三场景拦截验证；
   - **业务异常与事务原子性**（[tests/test_interface_material_negative.py](tests/test_interface_material_negative.py)）：前置自建临时商品测重复条码（`code=8000005`）、超 DB 长度边界 101 字符（`code=301`）、多明细部分重复整单回滚校验；
   - **端到端进销存业务流 + MySQL 双重断言**（[tests/test_interface_purchase_flow.py](tests/test_interface_purchase_flow.py)）：**供应商建档 → 商品建档 → 采购入库（数量 5）→ 接口与 `jsh_material_current_stock` 核对涨至 5 → 删单冲销 → 接口与数据库核对逻辑删（`delete_flag='1'`）及库存归 0 → 逆序自动清理**。
2. **可追溯用例设计与缺陷闭环**：
   - 新增商品 20 条用例设计表（等价类、边界值、判定表/组合、错误推测）：[material_add_cases.xlsx](material_add_cases.xlsx)
   - 用例与自动化脚本映射表：[API_TRACEABILITY.md](API_TRACEABILITY.md)
   - 接口契约与 DB 表结构速查：[API_REFERENCE.md](API_REFERENCE.md)
   - 真实缺陷记录（含 UI + API + 源码交叉证据链，`ERP-001` ~ `ERP-004`）：[BUGS.md](BUGS.md)
3. **UI 自动化测试基线（5 条）**：
   - 使用 Playwright 完成登录及商品必填/新增/编辑链路（[tests/test_login.py](tests/test_login.py)、[tests/test_material_validation.py](tests/test_material_validation.py)）。
4. **CI 持续集成检查**：
   - 配置 GitHub Actions 工作流（[.github/workflows/api-tests.yml](.github/workflows/api-tests.yml)），在每次提交/PR 时自动安装依赖、校验 Python 语法与用例收集完整性。

---

## 二、测试环境与运行方式

### 1. 依赖安装
Python 3.12+；环境配置通过 `.env` 管理（口令与数据库连接信息不提交至仓库）：

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env   # 填入 ERP_BASE_URL / ERP_USERNAME / ERP_PASSWORD 及 DB_* 配置
```

如需运行 Playwright UI 用例，额外执行一次浏览器安装：
```bash
python -m playwright install chromium
```

### 2. 运行正式接口自动化并生成 Allure 报告
确认 jshERP 服务运行正常（`http://127.0.0.1:18090/`）：

```bash
cd /home/AmazingYe/erp-ui-tests
source .venv/bin/activate

# 运行全部 11 条正式接口用例并收集 Allure 原始结果
pytest -v \
  tests/test_interface_login.py \
  tests/test_interface_material.py \
  tests/test_interface_auth.py \
  tests/test_interface_material_negative.py \
  tests/test_interface_purchase_flow.py \
  --alluredir=reports/allure-results --clean-alluredir

# 生成并查看 HTML 报告（需本机安装 Java 17+ 与 allure CLI）
allure generate reports/allure-results -o reports/allure-report --clean
allure open reports/allure-report
```

### 3. 运行 Playwright UI 自动化
```bash
pytest -v tests/test_login.py tests/test_material_validation.py
```

---

## 三、项目结构

```text
.github/workflows/api-tests.yml          GitHub Actions CI 语法与用例收集流水线
conftest.py                              配置加载、登录鉴权、material_cleaner、db_conn fixture
common/common_tools.py                   UI 公共工具（随机名称与单商品清理）
tests/
  test_interface_login.py                认证登录与商品列表只读用例
  test_interface_material.py             商品新增/查询/清理闭环
  test_interface_auth.py                 无/错/登出失效 token 鉴权异常用例
  test_interface_material_negative.py    重复条码、超长边界、多明细回滚异常用例
  test_interface_purchase_flow.py        采购入库与删单冲销业务流（API + DB 双重断言）
  test_login.py                          Playwright 登录 UI 用例
  test_material_validation.py            Playwright 商品表单校验/新增/编辑 UI 用例
material_add_cases.xlsx                  新增商品用例设计表（20 条）
API_REFERENCE.md                         接口契约与 MySQL 表结构速查手册
API_TRACEABILITY.md                      用例编号与脚本可追溯对照表
BUGS.md                                  缺陷档案（ERP-001 ~ ERP-004）
deploy/                                  容器部署配置（含 Nginx 动态 DNS 修复）
```

---

## 四、关键工程设计说明

- **数据隔离与失败必清理**：接口用例均使用带 `uuid` 的随机测试数据；`material_cleaner` 采用 `yield` fixture 保证用例失败后仍自动回收商品；采购业务流在 `try ... finally` 中按 **入库单 → 商品 → 供应商** 的依赖逆序清理，避免业务引用阻塞删除。
- **接口 + DB 双重断言**：通过 `PyMySQL` 直连测试库（启用 `DictCursor` 与 `autocommit=True` 避开长连接事务隔离级别读不到新写数据），校验 `jsh_depot_head` 逻辑删除标记与 `jsh_material_current_stock` 实时库存变化。
- **频控避坑（`ERP-001`）**：jshERP 后端日志模块在同秒高频请求时会清除登录会话，写/删操作之间统一保留 `time.sleep(2)` 规避误杀。
