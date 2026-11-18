# jshERP 接口与数据库表备忘

整理测试过程中用到的接口地址、请求参数、实测返回以及 MySQL 校验表结构。

## 公共约定

- 服务地址：`http://127.0.0.1:18090`，接口前缀 `/jshERP-boot`
- 鉴权头：`x-access-token: <token>`，JSON 请求带 `Content-Type: application/json`
- 同秒频控（`ERP-001`）：写/删请求之间加 `time.sleep(2)`，避免触发同秒清 session
- 未登录或 token 失效响应（`ERP-004`）：返回 `HTTP 500` + 纯文本 `"loginOut"`（不是 JSON）
- 业务流清理顺序：入库单 → 商品 → 供应商

## 一、认证接口（`user`）

### 1. 登录 `POST /jshERP-boot/user/login`

不需要 `x-access-token`。请求体：

```json
{
  "loginName": "<用户名>",
  "password": "<32位小写MD5>",
  "uuid": "<随机串，如 uuid4().hex>"
}
```

成功响应（HTTP 200）：

```json
{
  "code": 200,
  "data": {
    "token": "<会话token>",
    "user": {
      "id": 63,
      "loginName": "<用户名>",
      "status": 0
    }
  }
}
```

### 2. 退出登录 `GET /jshERP-boot/user/logout`

请求头带 `x-access-token`，无额外参数。实测返回 HTTP 200：

```json
{
  "code": 400,
  "data": null
}
```

虽然业务 `code` 是 `400`，但后端已经清理掉 Redis 里的登录状态，再用该 `token` 访问其他接口会返回 `500 "loginOut"`。

## 二、商品接口（`material`）

### 1. 新增商品 `POST /jshERP-boot/material/add`

最小合法请求体：

```json
{
  "name": "API调研商品_974f53ed",
  "standard": "500ml",
  "unit": "瓶",
  "meList": [
    {
      "barCode": "84123456789012345678",
      "commodityUnit": "瓶",
      "sku": ""
    }
  ],
  "stock": [],
  "sortList": [],
  "meDeleteIdList": []
}
```

- `stock`、`sortList`、`meDeleteIdList` 必须保留空数组，缺少会报错；`meList` 为明细列表，正常至少 1 条。
- 正常返回：`{"code": 200, "data": {"message": "成功"}}`
- 条码重复：`{"code": 8000005, "data": {"message": "商品条码:1036重复"}}`
- 字段超 DB 长度（`name > 100` 或 `unit > 50`）：`{"code": 301, "data": {"message": "数据写入异常"}}`
- 后端未校验空值、`barCode` 长度与空 `meList` 的情况见 `BUGS.md` 中的 `ERP-002`。

### 2. 查询商品列表 `GET /jshERP-boot/material/list`

Query 参数：`search=json.dumps({"materialParam": "商品名或条码"}, ensure_ascii=False)`、`currentPage=1`、`pageSize=10`（可选 `column="createTime"`、`order="desc"`）。

返回示例：

```json
{
  "code": 200,
  "data": {
    "total": 1,
    "rows": [
      {
        "id": 757,
        "name": "API落库校验_025f5833",
        "standard": "500ml",
        "unit": "瓶",
        "mBarCode": "293707705829032169",
        "stock": 0.0,
        "initialStock": 0.0,
        "enabled": true,
        "tenantId": 63,
        "deleteFlag": "0",
        "attribute": "{}"
      }
    ]
  }
}
```

`materialParam` 是模糊查询，断言时需过滤 `r["name"] == target`；`stock` 字段反映当前库存。

### 3. 批量删除商品 `DELETE /jshERP-boot/material/deleteBatch`

Query 参数 `ids="757"`（多个用逗号分隔），成功返回 `{"code": 200, "data": {"message": "成功"}}`。若商品已被单据明细引用，会拒绝删除。

## 三、供应商接口（`supplier`）

### 1. 新增供应商 `POST /jshERP-boot/supplier/add`

最小合法体只需传 `{"supplier": "小王", "type": "供应商"}`（其他联系人、电话、税号等均为选填）。成功返回 `{"code": 200, "data": {"message": "成功"}}`。

### 2. 查询供应商列表 `GET /jshERP-boot/supplier/list`

Query 参数：`search=json.dumps({"supplier": "名称", "type": "供应商"}, ensure_ascii=False)`、`currentPage=1`、`pageSize=10`。

返回示例：

```json
{
  "code": 200,
  "data": {
    "total": 1,
    "rows": [
      {
        "id": 91,
        "supplier": "供应商4",
        "type": "供应商",
        "enabled": true,
        "deleteFlag": "0"
      }
    ]
  }
}
```

### 3. 删除供应商 `DELETE /jshERP-boot/supplier/delete`

Query 参数 `id=<supplier_id>`，成功返回 `{"code": 200, "data": {"message": "成功"}}`。

## 四、采购入库与单据接口（`depotHead`）

### 1. 新增采购入库单 `POST /jshERP-boot/depotHead/addDepotHeadAndDetail`

注意：`info` 和 `rows` 必须是双重序列化的 JSON 字符串（先 `json.dumps` 成字符串再放进外层 JSON，不能直接传对象或数组）。下面按数量 `5`、单价 `10` 示意：

```json
{
  "info": "{\"defaultNumber\":\"CGRK00000000673\",\"organId\":57,\"operTime\":\"2026-11-16 23:41:53\",\"number\":\"CGRK00000000673\",\"discount\":0,\"discountMoney\":0,\"discountLastMoney\":50,\"otherMoney\":0,\"accountId\":17,\"changeAmount\":-50,\"debt\":0,\"type\":\"入库\",\"subType\":\"采购\",\"totalPrice\":-50,\"accountIdList\":\"\",\"accountMoneyList\":\"\",\"fileName\":\"\",\"status\":\"0\"}",
  "rows": "[{\"id\":\"17948437134310439943\",\"name\":\"商品名称\",\"unit\":\"瓶\",\"operNumber\":5,\"unitPrice\":10,\"allPrice\":50,\"taxRate\":0,\"taxMoney\":0,\"taxLastMoney\":50,\"remark\":\"\",\"linkId\":\"\",\"depotId\":\"14\",\"barCode\":\"<商品条码>\"}]"
}
```

- `info`：`organId` 为供应商 ID，`number`/`defaultNumber` 为唯一单号，`accountId=17` 为账户1，`status="0"` 未审核 / `"1"` 已审核，付款金额 `totalPrice` 与 `changeAmount` 传负值。
- `rows`：后端通过 `barCode` 查找 `jsh_material_extend` 关联商品，`depotId="14"` 为仓库1。
- 成功返回 `{"msg": "操作成功", "code": 200}`（这里是 `msg`，不是 `data.message`）。
- 当前环境 `force_approval_flag='0'`（未开启强审核），保存入库单后库存立即增加。

### 2. 查询单据列表 `GET /jshERP-boot/depotHead/list`

Query 参数：`search=json.dumps({"number": "单号", "type": "入库", "subType": "采购"}, ensure_ascii=False)`、`currentPage=1`、`pageSize=10`。

返回字段包含 `data.total` 与 `data.rows`（每行含 `id`、`number`、`organName`、`status`；无数据时 `total: 0, rows: []`）。

### 3. 审核 / 反审核 `POST /jshERP-boot/depotHead/batchSetStatus`

请求体：`{"status": 1, "ids": "277,"}`（`1` 审核、`0` 反审核），成功返回 `{"code": 200, "data": {"message": "成功"}}`。

### 4. 删除单据 `DELETE /jshERP-boot/depotHead/deleteBatch`

Query 参数 `ids=277,`，成功返回 `{"code": 200, "data": {"message": "成功"}}`。删除入库单后会同步重算并扣减实时库存。

## 五、MySQL 校验表（`jsh_erp`）

| 表名 | 说明 | 常用字段 | 逻辑删除标记 |
|---|---|---|---|
| `jsh_material` | 商品主表 | `id`, `name` (`varchar(100)`), `unit` (`varchar(50)`), `standard` | `delete_flag` (`'0'`/`'1'`) |
| `jsh_material_extend` | 商品条码/价格表 | `id`, `material_id`, `bar_code` (`varchar(50)`), `commodity_unit` | `delete_Flag`（注意大写 `F`） |
| `jsh_supplier` | 供应商表 | `id`, `supplier`, `type` (`'供应商'`) | `delete_flag` |
| `jsh_depot_head` | 单据主表 | `id`, `type`, `sub_type`, `number`, `organ_id`, `status` | `delete_flag` |
| `jsh_depot_item` | 单据明细表 | `header_id`, `material_id`, `depot_id`, `oper_number`, `unit_price`, `all_price` | `delete_flag` |
| `jsh_material_current_stock` | 实时库存表 | `material_id`, `depot_id`, `current_number` (`decimal(24,6)`) | `delete_flag` |

本地测试库基础 ID：仓库 `14`（仓库1）/ `15`（仓库2）/ `17`（仓库3）；账户 `17`（账户1）/ `18`（账户2）；`jsh_system_config` 中 `force_approval_flag = '0'`、`minus_stock_flag = '1'`。
