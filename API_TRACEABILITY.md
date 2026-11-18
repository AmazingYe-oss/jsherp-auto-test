# 接口用例与自动化脚本对应表

记录现有 11 条接口自动化用例、新增商品 20 条设计用例与缺陷的对应关系。

## 接口自动化用例（11 条）

| 用例编号 | 模块 | 用例说明 | 对应脚本（`pytest` 节点） | 断言与清理要点 | 关联缺陷 |
|---|---|---|---|---|---|
| `API-AUTH-001` | 认证与查询 | 正确账号密码（32位小写MD5）登录成功 | `tests/test_interface_login.py::test_login` | `code == 200`、`status == 0`、`token` 非空 | - |
| `API-MAT-READ-001` | 认证与查询 | 携带有效 token 查询商品列表 | `tests/test_interface_login.py::test_login_and_list` | `code == 200`、`total >= 0`、字段类型与值 | - |
| `TC-MAT-ADD-001` | 商品管理 | 新增商品（最小合法集）→ 查询验证 → 删除 | `tests/test_interface_material.py::test_material_crud` | `code == 200`、精确匹配1条、条码一致；`material_cleaner` 自动删 | - |
| `API-AUTH-002` | 接口鉴权 | 不传 `x-access-token` 访问 `/material/list` | `tests/test_interface_auth.py::test_material_list_without_token` | `HTTP 500` + `"loginOut"` | `ERP-004` |
| `API-AUTH-003` | 接口鉴权 | 传无效 `x-access-token` 访问 `/material/list` | `tests/test_interface_auth.py::test_material_list_with_invalid_token` | `HTTP 500` + `"loginOut"` | `ERP-004` |
| `API-AUTH-004` | 接口鉴权 | 登录后调用 `/user/logout` 使 token 失效再访问 | `tests/test_interface_auth.py::test_material_list_with_expired_token` | 登出前 `200` 查列表；登出后同一 token 返回 `500 "loginOut"` | `ERP-004` |
| `TC-MAT-ADD-003` | 商品异常 | 新增商品条码与已有商品重复 | `tests/test_interface_material_negative.py::test_tc_mat_add_003_duplicate_barcode` | `code == 8000005`，商品B未入库；自建前置商品A并自动清理 | - |
| `TC-MAT-ADD-006` | 商品边界 | 新增商品 `name` 为 101 字符（超 DB 上限 100） | `tests/test_interface_material_negative.py::test_tc_mat_add_006_overlength_name` | `code == 301`（`数据写入异常`），未入库；`material_cleaner` 兜底 | `ERP-003` |
| `TC-MAT-ADD-019` | 商品事务 | `meList` 传 2 条明细且第 2 条条码重复 | `tests/test_interface_material_negative.py::test_tc_mat_add_019_with_two_barcode` | `code == 8000005`，第1条新条码无残留（整单回滚），前置商品完好 | - |
| `API-FLOW-001` | 业务流+DB | 新增商品后核对 MySQL 落库一致性 | `tests/test_interface_purchase_flow.py::test_db_demo_material_sync` | 直查 `jsh_material` JOIN `jsh_material_extend` 一致；自动清理 | - |
| `API-FLOW-002` | 业务流+DB | 供应商→商品→采购入库(5)→删单冲销 | `tests/test_interface_purchase_flow.py::test_purchase_in_and_reverse_flow` | 接口 `stock`（5→0）+ DB `current_number`（5→0）+ `delete_flag=='1'`；`finally` 逆序清理 | - |

## 新增商品用例设计清单（[material_add_cases.xlsx](material_add_cases.xlsx)）

| 用例编号 | 设计方法 / 维度 | 优先级 | 方式 | 状态 / 备注 |
|---|---|---|---|---|
| `TC-MAT-ADD-001` | 有效等价类（最小合法集） | P0 | 自动化 | 已转 `test_material_crud` |
| `TC-MAT-ADD-002` | 无效等价类（`name=""`） | P1 | 自动化 | 接口实测放行入库（`code=200`），记入 `ERP-002` |
| `TC-MAT-ADD-003` | 无效等价类（条码重复） | P0 | 自动化 | 已转 `test_tc_mat_add_003_duplicate_barcode` |
| `TC-MAT-ADD-004` | 无效等价类（`name=" "` 纯空格） | P2 | 手工 | 接口实测放行入库，记入 `ERP-002` |
| `TC-MAT-ADD-005` | 边界值（`name` 长度=100） | P1 | 自动化 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-006` | 边界值（`name` 长度=101） | P1 | 自动化 | 已转 `test_tc_mat_add_006_overlength_name`，关联 `ERP-003` |
| `TC-MAT-ADD-007` | 边界值（`name` 长度=1） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-008` | 无效等价类（`name=null`） | P1 | 自动化 | 接口实测放行入库，记入 `ERP-002` |
| `TC-MAT-ADD-009` | 无效等价类（`unit=""`） | P1 | 自动化 | 接口实测放行入库，记入 `ERP-002` |
| `TC-MAT-ADD-010` | 无效等价类（`unit=" "` 纯空格） | P2 | 手工 | 接口实测放行入库，记入 `ERP-002` |
| `TC-MAT-ADD-011` | 边界值（`unit` 长度=50） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-012` | 边界值（`unit` 长度=51） | P1 | 自动化 | 接口实测返回 `code=301 数据写入异常`，记入 `ERP-003` |
| `TC-MAT-ADD-013` | 无效等价类（`commodityUnit=""`） | P1 | 自动化 | 接口实测放行入库，记入 `ERP-002` |
| `TC-MAT-ADD-014` | 边界值（`barCode` 长度=4） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-015` | 边界值（`barCode` 长度=3） | P1 | 自动化 | 接口实测放行入库（前端限 4~40），记入 `ERP-002` |
| `TC-MAT-ADD-016` | 边界值（`barCode` 长度=40） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-017` | 边界值（`barCode` 长度=41） | P1 | 自动化 | 接口实测放行入库（DB `varchar(50)`），记入 `ERP-002` |
| `TC-MAT-ADD-018` | 组合（`unit` 与 `commodityUnit` 不一致） | P2 | 手工 | 接口实测放行入库，缺少联动校验 |
| `TC-MAT-ADD-019` | 组合/事务（2条明细第2条重复回滚） | P1 | 自动化 | 已转 `test_tc_mat_add_019_with_two_barcode` |
| `TC-MAT-ADD-020` | 边界/错误推测（`meList=[]`） | P1 | 自动化 | 接口实测生成无条码商品，记入 `ERP-002` |
