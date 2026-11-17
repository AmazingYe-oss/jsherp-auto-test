# jshERP 接口测试用例与自动化脚本对照表（可追溯矩阵）

> 设计原则：**用例设计先于自动化；自动化脚本与用例编号一一对应；覆盖正向链路、等价类/边界值、鉴权异常、业务流与 MySQL 双重断言。**

---

## 一、接口自动化脚本汇总（共 11 条）

| 序号 | 用例编号 / 场景归属 | 模块 | 用例描述 | 自动化脚本（`pytest` 节点） | 断言要点 & 数据清理 | 关联缺陷 |
|---|---|---|---|---|---|---|
| 1 | `API-AUTH-001` | 认证与查询 | 正确账号密码（32位小写MD5）登录成功 | `tests/test_interface_login.py::test_login` | `code == 200`、`status == 0`、`token` 非空 | - |
| 2 | `API-MAT-READ-001` | 认证与查询 | 携带有效 token 查询商品列表 | `tests/test_interface_login.py::test_login_and_list` | `code == 200`、`total >= 0`、字段类型与值 | - |
| 3 | `TC-MAT-ADD-001` | 商品管理 | 新增商品（最小合法集）→ 查询验证 → 删除 | `tests/test_interface_material.py::test_material_crud` | `code == 200`、精确匹配1条、条码一致；`material_cleaner` 自动删 | - |
| 4 | `API-AUTH-002` | 接口鉴权 | 不传 `x-access-token` 访问 `/material/list` | `tests/test_interface_auth.py::test_material_list_without_token` | `HTTP 500` + `"loginOut"` | `ERP-004` |
| 5 | `API-AUTH-003` | 接口鉴权 | 伪造无效 `x-access-token` 访问 `/material/list` | `tests/test_interface_auth.py::test_material_list_with_invalid_token` | `HTTP 500` + `"loginOut"` | `ERP-004` |
| 6 | `API-AUTH-004` | 接口鉴权 | 登录后主动 `/user/logout` 使 token 失效再访问 | `tests/test_interface_auth.py::test_material_list_with_expired_token` | 登出前 `200` 查列表；登出后同一 token 返回 `500 "loginOut"` | `ERP-004` |
| 7 | `TC-MAT-ADD-003` | 商品异常 | 新增商品条码与前置临时商品重复 | `tests/test_interface_material_negative.py::test_tc_mat_add_003_duplicate_barcode` | `code == 8000005`（含`"重复"`），商品B未入库；自建前置A并清理 | - |
| 8 | `TC-MAT-ADD-006` | 商品边界 | 新增商品 `name` 为严格 101 字符（超 DB `varchar(100)`） | `tests/test_interface_material_negative.py::test_tc_mat_add_006_overlength_name` | `code == 301`（`"数据写入异常"`），列表未入库；`material_cleaner` 兜底 | `ERP-003` |
| 9 | `TC-MAT-ADD-019` | 商品事务 | `meList` 传 2 条明细且第 2 条条码重复（整单回滚） | `tests/test_interface_material_negative.py::test_tc_mat_add_019_with_two_barcode` | `code == 8000005`，按第1条新条码查询为 0 条（事务回滚），前置商品完好 | - |
| 10 | `API-FLOW-001` | 业务流+DB | 新增商品后接口与 MySQL 落库一致性校验 | `tests/test_interface_purchase_flow.py::test_db_demo_material_sync` | 直查 `jsh_material` JOIN `jsh_material_extend` 核对一致；自动清理 | - |
| 11 | `API-FLOW-002` | 业务流+DB | 供应商→商品→采购入库(5)→库存涨→删单冲销→库存归0 | `tests/test_interface_purchase_flow.py::test_purchase_in_and_reverse_flow` | 接口 `stock`（5→0）+ DB `jsh_material_current_stock.current_number`（5→0）+ `jsh_depot_head.delete_flag=='1'`；`finally` 逆序清理 | - |

---

## 二、「新增商品」用例设计覆盖分布（[material_add_cases.xlsx](material_add_cases.xlsx)，共 20 条）

| 用例编号 | 测试维度 / 设计方法 | 优先级 | 规划方式 | 实测落地状态 / 备注 |
|---|---|---|---|---|
| `TC-MAT-ADD-001` | 有效等价类（最小合法集） | P0 | 自动化 | 已实现为自动化用例 `test_material_crud` |
| `TC-MAT-ADD-002` | 无效等价类（`name=""`） | P1 | 自动化 | 接口实测放行入库（`code=200`），已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-003` | 无效等价类（条码重复） | P0 | 自动化 | 已实现为自动化用例 `test_tc_mat_add_003_duplicate_barcode` |
| `TC-MAT-ADD-004` | 无效等价类（`name=" "`纯空格） | P2 | 手工 | 接口实测放行入库，已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-005` | 边界值（`name` 长度=100 上边界） | P1 | 自动化 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-006` | 边界值（`name` 长度=101 超上边界） | P1 | 自动化 | 已实现为自动化用例 `test_tc_mat_add_006_overlength_name`（`code=301`），关联 `ERP-003` |
| `TC-MAT-ADD-007` | 边界值（`name` 长度=1 下边界） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-008` | 无效等价类（`name=null`） | P1 | 自动化 | 接口实测放行入库，已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-009` | 无效等价类（`unit=""`） | P1 | 自动化 | 接口实测放行入库，已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-010` | 无效等价类（`unit=" "`纯空格） | P2 | 手工 | 接口实测放行入库，已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-011` | 边界值（`unit` 长度=50 上边界） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-012` | 边界值（`unit` 长度=51 超上边界） | P1 | 自动化 | 接口实测返回 `code=301 数据写入异常`，已归档缺陷 `ERP-003` |
| `TC-MAT-ADD-013` | 无效等价类（`commodityUnit=""`） | P1 | 自动化 | 接口实测放行入库，已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-014` | 边界值（`barCode` 长度=4 下边界） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-015` | 边界值（`barCode` 长度=3 低于下边界） | P1 | 自动化 | 接口实测放行入库（前端限 4~40），已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-016` | 边界值（`barCode` 前端上边界 40） | P2 | 手工 | 接口实测 `code=200` 正常入库并清理 |
| `TC-MAT-ADD-017` | 边界值（`barCode` 超前端上边界 41） | P1 | 自动化 | 接口实测放行入库（DB `varchar(50)`），已归档缺陷 `ERP-002` |
| `TC-MAT-ADD-018` | 判定表/组合（`unit` 与 `commodityUnit` 不一致） | P2 | 手工 | 接口实测放行入库，记为校验缺口 |
| `TC-MAT-ADD-019` | 组合/事务（2条明细第2条条码重复回滚） | P1 | 自动化 | 已实现为自动化用例 `test_tc_mat_add_019_with_two_barcode` |
| `TC-MAT-ADD-020` | 边界/错误推测（`meList=[]` 空明细） | P1 | 自动化 | 接口实测生成无条码商品，已归档缺陷 `ERP-002` |
