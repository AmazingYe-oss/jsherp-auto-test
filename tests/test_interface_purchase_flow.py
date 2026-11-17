"""采购入库端到端业务流测试：供应商 -> 商品 -> 入库单 -> 库存变化 -> 删单冲销（API + DB 双重断言）。"""

import time
from uuid import uuid4
import requests
import json
from datetime import datetime
import allure

@allure.feature("商品接口")
@allure.story("新增商品与 MySQL 落库对账")
@allure.title("打通接口 + MySQL 双重断言：新增商品后直查 jsh_material / jsh_material_extend 核对落库")
def test_db_demo_material_sync(base_url, login_interface, material_cleaner, db_conn):
    """打通接口 + MySQL 双重断言：新增商品后直查 jsh_material / jsh_material_extend 核对落库。"""
    headers = {"x-access-token": login_interface["token"], "Content-Type": "application/json"}
    name = f"API落库校验_{uuid4().hex[:8]}"
    barcode = str(uuid4().int)[:18]
    with allure.step("1. 预先登记商品自动清理（material_cleaner）"):
        material_cleaner(name)

    with allure.step("2. 发送新增商品请求并校验返回"):
        time.sleep(2)
        resp = requests.post(
            f"{base_url}/jshERP-boot/material/add",
            json={
                "name": name,
                "standard": "500ml",
                "unit": "瓶",
                "meList": [{"barCode": barcode, "commodityUnit": "瓶", "sku": ""}],
                "stock": [],
                "sortList": [],
                "meDeleteIdList": [],
            },
            headers=headers,
            timeout=10,
        )
        assert resp.status_code == 200, resp.text
        assert resp.json()["code"] == 200, resp.json()

    with allure.step("3. 使用 db_conn 直查 MySQL 核对落库"):
        with db_conn.cursor() as cur:
            cur.execute(
                """
                SELECT m.id, m.name, m.unit, m.delete_flag, me.bar_code
                FROM jsh_material m
                JOIN jsh_material_extend me ON m.id = me.material_id
                WHERE m.name = %s AND m.delete_flag = '0' AND me.delete_Flag = '0'
                """,
                (name,),
            )
            rows = cur.fetchall()

        print("\n[DB 查询结果]", rows)
        assert len(rows) == 1, f"DB 应恰好落库 1 条，实际: {rows}"
        assert rows[0]["name"] == name
        assert rows[0]["unit"] == "瓶"
        assert rows[0]["bar_code"] == barcode


@allure.feature("采购入库业务流")
@allure.story("采购入库与删单冲销（API + DB 双重断言）")
@allure.title("端到端业务流：供应商→商品→采购入库(5)→查库涨至5→删单冲销→查库归0")
def test_purchase_in_and_reverse_flow(base_url, login_interface, material_cleaner, db_conn):
    token = login_interface["token"]
    headers = {"x-access-token": token, "Content-Type": "application/json"}
    sup_name = f"供应商{uuid4().hex[:8]}"
    ids = []
    depot_head_id = None

    try:
        time.sleep(2)
        with allure.step("新增供应商"):
        
            response_add_supplier = requests.post(
                f"{base_url}/jshERP-boot/supplier/add",
                headers=headers,
                json={"supplier": sup_name, "type": "供应商"},
                timeout=10,
            )

            assert response_add_supplier.status_code == 200
            assert response_add_supplier.json()["code"] == 200

        time.sleep(2)
        with allure.step("查询供应商"):
            response_list = requests.get(
            f"{base_url}/jshERP-boot/supplier/list",
            params={
                "search": json.dumps(
                    {"supplier": sup_name, "type": "供应商"},
                    ensure_ascii=False,
                ),
                "currentPage": 1,
                "pageSize": 10,
            },
            headers=headers,
            timeout=10,
        )

            assert response_list.status_code == 200
            list_result = response_list.json()
            assert list_result["code"] == 200

            rows = list_result["data"]["rows"]
            ids = [
                row["id"]
                for row in rows
                if row["supplier"] == sup_name
            ]
            assert len(ids) == 1, f"新增供应商后应精确查到 1 条，实际: {rows}"

        mat_name = f"商品{uuid4().hex[:8]}"
        barcode = str(uuid4().int)[:18]
        material_cleaner(mat_name)

        time.sleep(2)
        with allure.step("新增商品"):
            response_material_add = requests.post(
                f"{base_url}/jshERP-boot/material/add",
                headers=headers,
                json={
                    "name": mat_name,
                    "standard": "500ml",
                    "unit": "瓶",
                    "meList": [{"barCode": barcode, "commodityUnit": "瓶", "sku": ""}],
                    "stock": [],
                    "sortList": [],
                    "meDeleteIdList": [],
                },
                timeout=10,
            )
            assert response_material_add.status_code == 200
            assert response_material_add.json()["code"] == 200

        time.sleep(2)
        with allure.step("查询商品拿 material_id"):
            response_material_list = requests.get(
                f"{base_url}/jshERP-boot/material/list",
                params={
                    "search": json.dumps(
                        {"materialParam": mat_name},
                        ensure_ascii=False,
                    ),
                    "currentPage": 1,
                    "pageSize": 10,
                },
                headers=headers,
                timeout=10,
            )
            assert response_material_list.status_code == 200
            mat_list_result = response_material_list.json()
            assert mat_list_result["code"] == 200
            mat_rows = [r for r in mat_list_result["data"]["rows"] if r["name"] == mat_name]
            assert len(mat_rows) == 1, f"新增商品后应精确查到 1 条，实际: {mat_list_result}"
            material_id = mat_rows[0]["id"]

        bill_no = f"CGRK{uuid4().hex[:10].upper()}"
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        info = {
            "defaultNumber": bill_no, "number": bill_no, "organId": ids[0],
            "operTime": now_str, "type": "入库", "subType": "采购",
            "accountId": 17, "changeAmount": -50, "totalPrice": -50,
            "discount": 0, "discountMoney": 0, "discountLastMoney": 50,
            "otherMoney": 0, "debt": 0, "accountIdList": "", "accountMoneyList": "",
            "fileName": "", "status": "0",
        }
        detail_rows = [{
            "name": mat_name, "unit": "瓶", "barCode": barcode, "depotId": "14",
            "operNumber": 5, "unitPrice": 10, "allPrice": 50,
            "taxRate": 0, "taxMoney": 0, "taxLastMoney": 50, "remark": "", "linkId": "",
        }]
        payload = {
            "info": json.dumps(info, ensure_ascii=False),
            "rows": json.dumps(detail_rows, ensure_ascii=False),
        }
        time.sleep(2)
        with allure.step("新增采购入库单（数量5）"):
            response_addDepotHeadAndDetail = requests.post(
                f"{base_url}/jshERP-boot/depotHead/addDepotHeadAndDetail",
                headers=headers,
                json=payload,
                timeout=10,
            )
            assert response_addDepotHeadAndDetail.status_code == 200
            assert response_addDepotHeadAndDetail.json()["code"] == 200
            assert response_addDepotHeadAndDetail.json()["msg"] == "操作成功"

        time.sleep(2)
        with allure.step("查询入库单拿 head_id"):
            response_depotHeadList = requests.get(
                f"{base_url}/jshERP-boot/depotHead/list",
                params={
                    "search": json.dumps(
                        {"number": bill_no, "type": "入库", "subType": "采购"},
                        ensure_ascii=False,
                    ),
                    "currentPage": 1,
                    "pageSize": 10,
                },
                headers=headers,
                timeout=10,
            )
            assert response_depotHeadList.status_code == 200
            dh_list_result = response_depotHeadList.json()
            assert dh_list_result["code"] == 200
            dh_rows = [r for r in dh_list_result["data"]["rows"] if r["number"] == bill_no]
            assert len(dh_rows) == 1, f"新增入库单后应精确查到 1 条，实际: {dh_list_result}"
            depot_head_id = dh_rows[0]["id"]

        time.sleep(2)
        with allure.step("入库后双重断言：接口 stock=5 且 DB current_number=5"):
            response_material_list_again = requests.get(
                f"{base_url}/jshERP-boot/material/list",
                headers=headers,
                params={
                    "search": json.dumps(
                        {"materialParam": mat_name},
                        ensure_ascii=False,
                    ),
                    "currentPage": 1,
                    "pageSize": 10,
                },
                timeout=10,
            )
            assert response_material_list_again.status_code == 200
            mat_again_result = response_material_list_again.json()
            assert mat_again_result["code"] == 200
            matched_mat = [r for r in mat_again_result["data"]["rows"] if r["name"] == mat_name]
            assert len(matched_mat) == 1
            assert matched_mat[0]["stock"] == 5

            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM jsh_material_current_stock
                    WHERE material_id = %s AND depot_id = 14 AND delete_flag = '0'
                    """,
                    (material_id,),
                )
                cur_row = cur.fetchone()
                assert cur_row is not None, "DB 库存表未查到记录"
                assert float(cur_row["current_number"]) == 5

        bill_id = depot_head_id
        time.sleep(2)
        with allure.step("删除入库单触发库存冲销"):
            response_deletebatch_depotHead = requests.delete(
                f"{base_url}/jshERP-boot/depotHead/deleteBatch",
                headers=headers,
                params={"ids": depot_head_id},
                timeout=10,
            )
            assert response_deletebatch_depotHead.status_code == 200
            delete_dh_result = response_deletebatch_depotHead.json()
            assert delete_dh_result["code"] == 200
            assert delete_dh_result["data"]["message"] == "成功"
            depot_head_id = None

        time.sleep(2)
        with allure.step("冲销后双重断言：单据已逻辑删除且库存还原为0"):
            response_depotHead_list = requests.get(
                f"{base_url}/jshERP-boot/depotHead/list",
                params={
                    "search": json.dumps(
                        {"number": bill_no, "type": "入库", "subType": "采购"},
                        ensure_ascii=False,
                    ),
                    "currentPage": 1,
                    "pageSize": 10,
                },
                headers=headers,
                timeout=10,
            )
            assert response_depotHead_list.status_code == 200
            dh_list_result = response_depotHead_list.json()
            assert dh_list_result["code"] == 200
            remaining_bills = [r for r in dh_list_result["data"]["rows"] if r["number"] == bill_no]
            assert remaining_bills == [], f"删除入库单后应查不到记录，实际: {remaining_bills}"

            time.sleep(2)
            response_material_list_again = requests.get(
                f"{base_url}/jshERP-boot/material/list",
                headers=headers,
                params={
                    "search": json.dumps(
                        {"materialParam": mat_name},
                        ensure_ascii=False,
                    ),
                    "currentPage": 1,
                    "pageSize": 10,
                },
                timeout=10,
            )
            assert response_material_list_again.status_code == 200
            mat_again_result = response_material_list_again.json()
            assert mat_again_result["code"] == 200
            matched_mat = [r for r in mat_again_result["data"]["rows"] if r["name"] == mat_name]
            assert len(matched_mat) == 1, f"删除入库单后商品仍应存在，实际: {matched_mat}"
            assert matched_mat[0]["stock"] == 0, f"删单冲销后接口库存应还原为 0，实际: {matched_mat[0]['stock']}"

            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM jsh_depot_head
                    WHERE id = %s
                    """,
                    (bill_id,),
                )
                cur_row = cur.fetchone()
                assert cur_row is not None, f"DB 未查到单据 id={bill_id}"
                assert cur_row["delete_flag"] == '1'

            with db_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT * FROM jsh_material_current_stock
                    WHERE material_id = %s AND depot_id = 14 AND delete_flag = '0'
                    """,
                    (material_id,),
                )
                cur_row = cur.fetchone()
                assert cur_row is not None, "DB 库存表未查到记录"
                assert float(cur_row["current_number"]) == 0

    finally:
        if depot_head_id is not None:
            time.sleep(2)
            response_delete_depotHead = requests.delete(
                f"{base_url}/jshERP-boot/depotHead/deleteBatch",
                headers=headers,
                params={"ids": depot_head_id},
                timeout=10,
            )
            assert response_delete_depotHead.status_code == 200
            delete_dh_result = response_delete_depotHead.json()
            assert delete_dh_result["code"] == 200
            assert delete_dh_result["data"]["message"] == "成功"

        for supplier_id in ids:
            time.sleep(2)
            response_delete_supplier = requests.delete(
                f"{base_url}/jshERP-boot/supplier/delete",
                headers=headers,
                params={"id": supplier_id},
                timeout=10,
            )
            assert response_delete_supplier.status_code == 200
            delete_sup_result = response_delete_supplier.json()
            assert delete_sup_result["code"] == 200
            assert delete_sup_result["data"]["message"] == "成功"