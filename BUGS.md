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

## ERP-002 新增商品接口未校验必填字段与条码长度，脏数据直接入库

状态：已确认（Major / P1）；已核对前端校验、接口实测及后端源码，未修改被测代码。

### 触发场景和实际结果

UI 弹窗新增商品时，名称为空、单位为空或条码不在 4~40 位会被拦截提示。但直接调用 `POST /jshERP-boot/material/add`（带上有效 `x-access-token`），传入以下参数时接口全部返回 `HTTP 200` 且业务 `code=200`（`{"message": "成功"}`），数据直接写入数据库：
- `name` 为 `""`、`" "` 或 `null`
- `unit` 为 `""`、`" "`，或 `meList[0].commodityUnit` 为 `""`
- `meList[0].barCode` 为 3 位或 41 位
- `meList` 为空数组 `[]`（生成无条码商品）

预期：服务端与前端规则保持一致，对必填项、空白字符、条码长度（4~40 位）及明细非空进行校验，不合法时返回明确业务错误码并拒绝入库。

### 证据

- UI 用例 [tests/test_material_validation.py](tests/test_material_validation.py)（`UI-M-005`、`UI-M-007`）与前端源码 `jshERP-web/src/views/material/modules/MaterialModal.vue`（L369-377、L416-435）对名称、单位必填及条码 `/^.{4,40}$/` 均有校验。
- 接口实测记录见 [material_add_cases.xlsx](material_add_cases.xlsx) 与 [API_TRACEABILITY.md](API_TRACEABILITY.md)。
- 后端源码 `MaterialService.java::insertMaterial`（L161-170）直接反序列化 JSON 后调用 `materialMapperEx.insertSelectiveEx(m)` 落库，没有做非空或长度判断。

## ERP-003 商品单位前端漏配长度上限，且字段超长直接报 301“数据写入异常”

状态：已确认（Minor / P2）；已核对前端表单、数据库表结构与接口实测结果。

### 触发场景和实际结果

在新增商品弹窗的“单位”输入框输入超长字符时，前端未拦截提示字数上限，点击保存后提示“数据不合法”。直接调用 `POST /jshERP-boot/material/add` 传入 101 字符的 `name` 或 51 字符的 `unit` 时，接口均返回 `HTTP 200`、`code=301`、`{"message": "数据写入异常"}`，没有指明是哪个字段超限。

预期：前端应按数据库字段长度补全 `unit` 的 `max: 50` 限制；后端应在入库前校验长度并返回具体字段提示，而不是直接触发 SQL 异常。

### 证据

- 数据库 `jsh_material` 表结构中 `name` 为 `varchar(100)`，`unit` 为 `varchar(50)`。
- 前端源码 `MaterialModal.vue`（L416-436）为 `name`、`standard`、`model` 配置了 `max: 100`，`unit` 只配置了 `required: true`，漏配 `max: 50`。
- 接口回归用例 [tests/test_interface_material_negative.py](tests/test_interface_material_negative.py) 中 `test_tc_mat_add_006_overlength_name` 稳定复现返回 `code=301`。

## ERP-004 未登录或 token 失效访问业务接口返回 HTTP 500 纯文本 "loginOut"

状态：已确认（Minor / P2）；已通过接口自动化与过滤器源码核实。

### 触发场景和实际结果

不带 `x-access-token`、传伪造 token 或使用 `/jshERP-boot/user/logout` 注销后的 token 请求 `GET /jshERP-boot/material/list`，接口统一返回 `HTTP 500` 及纯文本 `"loginOut"`（不是 JSON）。

预期：鉴权失败返回 `HTTP 401`（或统一 JSON 格式的未登录提示），避免调用方按 JSON 解析时报错或误判为服务端 500 故障。

### 证据

- 接口用例 [tests/test_interface_auth.py](tests/test_interface_auth.py) 覆盖了无 token、无效 token 和登出后失效 token 三种情况，均返回 `status_code == 500` 且 `text == "loginOut"`；另测得 `/jshERP-boot/user/logout` 正常退出时返回 `HTTP 200, code=400, data=null`。
- 后端源码 `LogCostFilter.java`（L67-70）直接写死 `servletResponse.setStatus(500);` 与 `write("loginOut");`。
