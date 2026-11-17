# ERP 问题记录

## ERP-001 快速商品操作导致登录状态失效，删除返回500或编辑后跳回登录页

状态：已观察异常；日志、源码与增加间隔后的对照运行支持同秒频控解释。后台问题未修复，临时规避保留，不将本轮通过解释为缺陷关闭。

### 触发场景和实际结果

自动化快速新增并删除：删除HTTP响应可取得，但JSON业务code=500，后台出现NullPointerException。自动化快速新增并编辑：全量回归 4 passed、1 failed，查询框超时，失败截图实际是登录页。

预期：有效登录下允许操作时正常完成；若触发频控或登录失效，应返回明确可处理的结果，不发生空指针。具体频控策略是否符合业务需求尚未确认。

### 证据

- 后台堆栈：UserService.getCurrentUser:507，经MaterialService.batchDeleteMaterialByIds:296调用。
- 同次删除日志按用户、商品模块、IP和当前秒查到count=1。
- 后续编辑失败日志中，新增和编辑同在16:48:37，商品操作计数为1，截图显示已回登录页。
- 源码：MaterialService删除前记录日志，再读当前用户；LogService.insertLog在同秒匹配记录count>0时调用RedisService.deleteObjectByUserAndIp，清除登录hash的userId；UserService.getCurrentUser对空userId直接.toString()，没有空值处理。

### 临时规避与验证

在删除前增加2秒间隔后，定向运行通过。进一步发现在编辑保存前也需要避开同秒操作。两处带原因的间隔保留；清理进入商品页后检查URL，避免登录页等待商品输入框。

修改间隔后连续多轮全量回归通过。该结果支持操作间隔的影响，但不证明所有时序与后台内部状态已被独立控制验证。

### 未做事项与影响

未修改被测源码、频控配置或用户登录记录；未通过降低断言要求接受500。失败运行可能留下商品，本项目不按前缀批量删除历史数据。未由测试直接确认每次失败后数据库最终状态，也不把逻辑删除描述成物理删除。

排查期间的临时trace与日志可能含敏感数据，不作为公开附件提交至仓库。

---

## ERP-002 新增商品接口缺少服务端必填与规则校验，前后端校验不一致致脏数据入库

- **缺陷级别**：Major（主要 / P1）
- **状态**：已确认（UI 规则、API 实测与后端源码已交叉验证；未修改被测系统源码）
- **模块**：商品管理 - 新增商品（`POST /jshERP-boot/material/add`）

### 前置条件
1. 被测 jshERP 服务正常运行；
2. 已登录获取有效 `x-access-token`（用于接口直连复现）。

### 复现步骤
1. **UI 路径对照**：进入“商品信息 → 新增商品”弹窗，将“名称”或“单位”留空后点击保存；或查看条码输入框校验。
2. **API 路径复现**：绕过前端页面，携带有效 `x-access-token` 直接向 `POST /jshERP-boot/material/add` 发送最小合法 JSON 的异常变体（如 `name=""`、`name=" "`、`name=null`、`unit=""`、`meList[0].commodityUnit=""`、`barCode` 为 3 位或 41 位、`meList=[]`）。
3. 调用 `GET /jshERP-boot/material/list`（或核查数据库）确认数据是否写入。

### 预期结果
前后端校验基线应一致：服务端应对必填字段（`name`、`unit`、`commodityUnit`、`barCode`）、首尾空白、条码长度（4~40 位）及明细非空（`meList` 至少 1 条）做同等校验，不合法请求应返回明确业务错误码并拒绝入库。

### 实际结果
1. UI 侧明确拦截空名称、空单位与非 4~40 位条码；
2. 但接口侧对上述 8 种非法输入**全部返回 `HTTP 200` 且业务 `code=200, data={"message":"成功"}`**，空名称、空单位、空明细（无条码）及超前端长度限制的条码均直接写入数据库（查询列表可检索到，测试结束后已清理）。

### 证据链（UI + API + 源码）
- **UI 证据**：UI 用例 [tests/test_material_validation.py](tests/test_material_validation.py)（`UI-M-007` 空名称拦截、`UI-M-005` 空单位拦截）及前端源码 `jshERP-web/src/views/material/modules/MaterialModal.vue`（L369-377、L416-435）明确定义必填与条码 `/^.{4,40}$/` 正则。
- **API 证据**：`POST /jshERP-boot/material/add` 参数等价类与边界实测记录见 [material_add_cases.xlsx](material_add_cases.xlsx) 与 [API_TRACEABILITY.md](API_TRACEABILITY.md)（对应 `TC-MAT-ADD-002/004/008/009/010/013/015/017/020`）。
- **后端源码定位**：`jshERP-boot/.../service/MaterialService.java` 中 `insertMaterial`（L161-170）直接反序列化 JSON 后调用 `materialMapperEx.insertSelectiveEx(m)` 落库，全程未对 `name`、`unit`、`meList` 及 `barCode` 长度做服务端校验（同时解释了环境中曾遗留“单位为空”脏数据的成因）。

---

## ERP-003 商品单位（unit）前端漏配最大长度校验，且超长入库直接报错 301“数据写入异常”

- **缺陷级别**：Minor（次要 / P2）
- **状态**：已确认（UI 现象、DB 表结构、API 自动化与源码已核实）
- **模块**：商品管理 - 新增商品

### 前置条件
1. 已登录获取有效会话/token；
2. 数据库字段约束：`jsh_material.name` 为 `varchar(100)`，`jsh_material.unit` 为 `varchar(50)`。

### 复现步骤
1. **UI 路径**：在“新增商品”弹窗“单位”输入框填入超过 50 个字符，点击保存。
2. **API 路径**：向 `POST /jshERP-boot/material/add` 分别发送 `name` 为 101 个字符（`TC-MAT-ADD-006`）或 `unit` 为 51 个字符（`TC-MAT-ADD-012`）。

### 预期结果
1. 前端表单应对 `unit` 配置与数据库一致的最大长度提示（`max: 50`），在提交前给出明确字数超限提示；
2. 后端应对超长参数返回具体可定位的参数校验提示（如“单位长度不能超过 50 个字符”），而非抛出模糊的数据库写入异常。

### 实际结果
1. UI 侧填写超长“单位”时无表单长度校验提示，点击保存发送请求后提示笼统的“数据不合法”；
2. 接口实测返回 `HTTP 200, code=301, data={"message":"数据写入异常"}`（未区分具体哪个字段超限）。

### 证据链（UI + DB + API + 源码）
- **UI 与前端源码**：`MaterialModal.vue`（L416-436）为 `name`/`standard`/`model` 均配置了 `max: 100`，唯独 `unit` 仅配 `{ required: true }`，漏配 `max: 50`。
- **DB 表结构**：`SHOW FULL COLUMNS FROM jsh_material` 确认 `name` 为 `varchar(100)`、`unit` 为 `varchar(50)`。
- **API 自动化**：[tests/test_interface_material_negative.py](tests/test_interface_material_negative.py) 中 `test_tc_mat_add_006_overlength_name`（严格 101 字符）稳定复现返回 `code=301, message="数据写入异常"`；`TC-MAT-ADD-012`（`unit` 51 字符）接口实测同样返回 `code=301`。

---

## ERP-004 未登录/无效或已登出 token 访问业务接口返回 HTTP 500 纯文本 "loginOut"，不符合鉴权状态码规范

- **缺陷级别**：Minor（次要 / P2，接口设计规范缺陷）
- **状态**：已确认（API 自动化与过滤器源码已核实）
- **模块**：全局鉴权拦截器（`LogCostFilter`）

### 前置条件
无有效会话（不带 `x-access-token`、传伪造字符串 token、或使用已调用 `GET /jshERP-boot/user/logout` 登出的 token）。

### 复现步骤
向业务接口 `GET /jshERP-boot/material/list` 发送请求，分别不传 `x-access-token`、传 `"invalid_token"`、或传登出后已失效的 token。

### 预期结果
返回标准未鉴权 HTTP 状态码（如 `401 Unauthorized`）及统一格式的 JSON 响应体（包含业务错误码与提示文案），便于前端与接口调用方统一解析。

### 实际结果
接口返回 **`HTTP 500`**（通常代表服务端内部崩溃），且响应体为非 JSON 纯文本 **`"loginOut"`**（调用方若按常规 JSON 解析会直接抛出 `JSONDecodeError`）。

### 证据链（API + 源码）
- **API 自动化**：[tests/test_interface_auth.py](tests/test_interface_auth.py) 中 3 条用例（无 token / 错 token / 登出失效 token）全部实测返回 `status_code == 500` 且 `text == "loginOut"`；另外测得 `GET /jshERP-boot/user/logout` 响应为 `HTTP 200, code=400, data=null`。
- **源码定位**：`jshERP-boot/.../filter/LogCostFilter.java`（L67-70）直接硬编码 `servletResponse.setStatus(500);` 与 `servletResponse.getWriter().write("loginOut");`。
