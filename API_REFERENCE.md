# jshERP 接口测试速查手册（参数、返回与坑点汇总）

> 本文汇总 jshERP 核心业务接口契约、参数规范、实测返回与 MySQL 校验表结构，供接口自动化用例编写与排错查阅（已脱敏，不含口令、MD5 或 token 真实值）。

---

## 全局约定与环境避坑

| 项目 | 约定 / 事实 |
|---|---|
| 服务入口与前缀 | `http://127.0.0.1:18090`，接口统一前缀 `/jshERP-boot` |
| 鉴权请求头 | `x-access-token: <token>`；JSON 接口带 `Content-Type: application/json` |
| 频控规避（`ERP-001`） | 同秒内连续操作会触发后台频控并清掉会话，**关键请求之间统一加 `time.sleep(2)`** |
| 未鉴权响应（`ERP-004`） | 不传 token / 错 token / 已登出 token 访问业务接口，均返回 **HTTP `500`** + 纯文本 **`"loginOut"`**（非 JSON，勿直接 `.json()`） |
| 断言原则 | 不只看 HTTP 200，必须校验业务 `code` + `data/rows` 内容（必要时辅以 MySQL 落库校验） |
| 清理顺序（业务流） | 存在外键/业务依赖时按逆序删除：**入库单 → 商品 → 供应商**，放入 `try ... finally` 或 `yield` fixture |

---

## 一、认证模块（`user`）

### 1. 登录 `POST /jshERP-boot/user/login`
- **鉴权**：不需要 `x-access-token`
- **请求体（JSON）**：
  ```json
  {
    "loginName": "jsh",
    "password": "<32位小写MD5>",
    "uuid": "<随机字符串，建议每次 uuid4().hex>"
  }
  ```
- **成功响应（HTTP 200）**：
  ```json
  {
    "code": 200,
    "data": {
      "token": "<会话token>",
      "user": {
        "id": 63,
        "loginName": "jsh",
        "status": 0
      }
    }
  }
  ```

### 2. 退出登录 `GET /jshERP-boot/user/logout`
- **鉴权**：请求头带 `x-access-token`
- **请求参数**：无
- **实测响应（HTTP 200）**：
  ```json
  {
    "code": 400,
    "data": null
  }
  ```
  > 注：虽业务 `code` 为 `400`，但实际会清除 Redis 中的会话，之后再用同一 `token` 访问业务接口会返回 `HTTP 500` + `"loginOut"`。

---

## 二、商品管理（`material`）

### 1. 新增商品 `POST /jshERP-boot/material/add`
- **鉴权**：需要 `x-access-token`
- **最小合法请求体（JSON）**：
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
  > **要点**：
  > - `stock`、`sortList`、`meDeleteIdList` 必须保留空数组占位，缺少会报错；
  > - `meList` 是列表（一商品多规格/多条码），最少传 1 条。

- **常见响应（HTTP 200）**：
  - **新增成功**：`{"code": 200, "data": {"message": "成功"}}`
  - **条码重复**：`{"code": 8000005, "data": {"message": "商品条码:1036重复"}}`
  - **字段超 DB 长度**（`name > 100` 或 `unit > 50`）：`{"code": 301, "data": {"message": "数据写入异常"}}`
  - **已知缺陷（`ERP-002`）**：后端未校验 `name`/`unit`/`commodityUnit` 为空或空格、未校验 `barCode` 长度（前端限 `4~40`，DB 为 `50`）、未校验 `meList` 为空数组，接口均会返回 `code: 200` 放行入库。

### 2. 查询商品列表 `GET /jshERP-boot/material/list`
- **鉴权**：需要 `x-access-token`
- **Query 参数**：
  - `search`：JSON 字符串，如 `'{"materialParam": "商品名称或条码"}'`（注意用 `json.dumps({"materialParam": ...}, ensure_ascii=False)`）
  - `currentPage`：`1`
  - `pageSize`：`10`
  - 可选排序：`column="createTime"`、`order="desc"`
- **成功响应（HTTP 200）**：
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
  > 注：`materialParam` 为模糊匹配，断言时需再用列表推导精确过滤 `r["name"] == target`；`stock` 字段会实时反映当前库存。

### 3. 批量删除商品 `DELETE /jshERP-boot/material/deleteBatch`
- **鉴权**：需要 `x-access-token`
- **Query 参数**（注意不是放在 JSON body）：
  - `ids`：逗号分隔的商品 `id` 字符串，如 `"757"` 或 `"757,758"`
- **成功响应（HTTP 200）**：
  ```json
  {
    "code": 200,
    "data": {
      "message": "成功"
    }
  }
  ```

---

## 三、供应商管理（`supplier`）

### 1. 新增供应商 `POST /jshERP-boot/supplier/add`
- **鉴权**：需要 `x-access-token`
- **最小合法请求体（JSON）**：
  ```json
  {
    "supplier": "小王",
    "type": "供应商"
  }
  ```
- **完整可选字段参考（F12 实抓）**：
  ```json
  {
    "supplier": "供应商4",
    "contacts": "阿伟",
    "telephone": "13888888888",
    "phoneNum": "12345678",
    "taxNum": "1314151",
    "taxRate": 13,
    "address": "bbbb",
    "description": "dawdaw",
    "type": "供应商"
  }
  ```
- **成功响应（HTTP 200）**：`{"code": 200, "data": {"message": "成功"}}`

### 2. 查询供应商列表 `GET /jshERP-boot/supplier/list`
- **鉴权**：需要 `x-access-token`
- **Query 参数**：
  - `search`：`json.dumps({"supplier": "名称", "type": "供应商"}, ensure_ascii=False)`
  - `currentPage`：`1`
  - `pageSize`：`10`
- **成功响应（HTTP 200）**：
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
- **鉴权**：需要 `x-access-token`
- **Query 参数**：`id=<supplier_id>`（例如 `?id=90`）
- **成功响应（HTTP 200）**：`{"code": 200, "data": {"message": "成功"}}`

---

## 四、采购入库与单据管理（`depotHead`）

### 1. 新增采购入库单 `POST /jshERP-boot/depotHead/addDepotHeadAndDetail`
- **鉴权**：需要 `x-access-token`
- **请求体（JSON）——核心坑点：`info` 和 `rows` 必须是双重序列化的 JSON 字符串（`json.dumps(...)`）！**（以下基于 F12 实抓结构，按数量 5、单价 10 示意）：
  ```json
  {
    "info": "{\"defaultNumber\":\"CGRK00000000673\",\"organId\":57,\"operTime\":\"2026-11-16 23:41:53\",\"number\":\"CGRK00000000673\",\"discount\":0,\"discountMoney\":0,\"discountLastMoney\":50,\"otherMoney\":0,\"accountId\":17,\"changeAmount\":-50,\"debt\":0,\"type\":\"入库\",\"subType\":\"采购\",\"totalPrice\":-50,\"accountIdList\":\"\",\"accountMoneyList\":\"\",\"fileName\":\"\",\"status\":\"0\"}",
    "rows": "[{\"id\":\"17948437134310439943\",\"name\":\"商品名称\",\"unit\":\"瓶\",\"operNumber\":5,\"unitPrice\":10,\"allPrice\":50,\"taxRate\":0,\"taxMoney\":0,\"taxLastMoney\":50,\"remark\":\"\",\"linkId\":\"\",\"depotId\":\"14\",\"barCode\":\"<商品条码>\"}]"
  }
  ```
  > **关键字段说明**：
  > - `info` 内：`organId` 为供应商 ID；`number` / `defaultNumber` 为唯一单据号；`type="入库"`、`subType="采购"`；`accountId=17`（账户1）；`status="0"`（未审核）或 `"1"`（已审核）；`totalPrice` / `changeAmount` 采购付款在前端传负值（如 `-50`）。
  > - `rows` 内：后端靠 **`barCode`** 匹配 `jsh_material_extend` 关联到具体商品；`depotId="14"`（仓库1）；`operNumber` 为入库数量。
  > - **库存时机**：当前系统 `force_approval_flag='0'`（未开强审核），保存入库单即更新当前库存。

- **成功响应（HTTP 200）**：
  ```json
  {
    "msg": "操作成功",
    "code": 200
  }
  ```
  > 注意：该接口返回的是 **`msg`**，不是 `data.message`！

### 2. 查询单据列表 `GET /jshERP-boot/depotHead/list`
- **鉴权**：需要 `x-access-token`
- **Query 参数**：
  - `search`：`json.dumps({"number": "单号", "type": "入库", "subType": "采购"}, ensure_ascii=False)`
  - `currentPage`：`1`
  - `pageSize`：`10`
- **响应示例（HTTP 200）**（当前环境无在库采购单时实测返回 `{"code": 200, "data": {"total": 0, "rows": []}}`；下例 `rows` 核心字段对照 `PurchaseInList.vue` 与 `DepotHeadMapperEx.xml`）：
  ```json
  {
    "code": 200,
    "data": {
      "total": 1,
      "rows": [
        {
          "id": 277,
          "number": "CGRK00000000673",
          "organName": "供应商名称",
          "status": "0"
        }
      ]
    }
  }
  ```

### 3. 批量审核 / 反审核 `POST /jshERP-boot/depotHead/batchSetStatus`
- **鉴权**：需要 `x-access-token`
- **请求体（JSON）**：
  ```json
  {
    "status": 1,
    "ids": "277,"
  }
  ```
  > `status`: `1` = 审核，`0` = 反审核；`ids` 为逗号分隔字符串（前端习惯末尾带逗号）。
- **成功响应（HTTP 200）**：`{"code": 200, "data": {"message": "成功"}}`

### 4. 删除单据（触发库存冲销） `DELETE /jshERP-boot/depotHead/deleteBatch`
- **鉴权**：需要 `x-access-token`
- **Query 参数**：`ids=277,`（逗号分隔单据 ID）
- **成功响应（HTTP 200）**：`{"code": 200, "data": {"message": "成功"}}`

---

## 五、MySQL 核心校验表速查（`jsh_erp`）

| 表名 | 用途 | 关键校验字段 | 逻辑删除字段 |
|---|---|---|---|
| `jsh_material` | 商品主表 | `id`, `name` (`varchar(100)`), `unit` (`varchar(50)`), `standard` | `delete_flag` (`'0'`/`'1'`) |
| `jsh_material_extend` | 商品条码/价格表 | `id`, `material_id`, `bar_code` (`varchar(50)`), `commodity_unit` | **`delete_Flag`**（大写 `F`） |
| `jsh_supplier` | 供应商/客户表 | `id`, `supplier`, `type` (`'供应商'`) | `delete_flag` |
| `jsh_depot_head` | 单据主表 | `id`, `type` (`'入库'`), `sub_type` (`'采购'`), `number`, `organ_id`, `status` | `delete_flag` |
| `jsh_depot_item` | 单据明细表 | `header_id`, `material_id`, `depot_id`, `oper_number`, `unit_price`, `all_price` | `delete_flag` |
| `jsh_material_current_stock` | 商品实时库存表 | `material_id`, `depot_id`, **`current_number`** (`decimal(24,6)`) | `delete_flag` |

**环境已有基础数据 ID 参考**：
- 仓库（`jsh_depot`）：`14`（仓库1）、`15`（仓库2）、`17`（仓库3）
- 账户（`jsh_account`）：`17`（账户1）、`18`（账户2）
- 系统配置（`jsh_system_config`）：`force_approval_flag = '0'`（未开强审核），`minus_stock_flag = '1'`（允许负库存）
