import json
import time
from uuid import uuid4
import requests
import allure


def build_material_payload(name, barcode, unit="瓶"):
    return {
        "name": name,
        "standard": "500ml",
        "unit": unit,
        "meList": [{"barCode": barcode, "commodityUnit": unit, "sku": ""}],
        "stock": [],
        "sortList": [],
        "meDeleteIdList": [],
    }

@allure.feature("商品接口")
@allure.story("新增商品")
@allure.title("TC-MAT-ADD-003：新增商品时条码与已有商品重复，应返回 8000005 拒绝且不写入商品 B。")
def test_tc_mat_add_003_duplicate_barcode(base_url, login_interface, material_cleaner):
    """TC-MAT-ADD-003：新增商品时条码与已有商品重复，应返回 8000005 拒绝且不写入商品 B。"""
    headers = {"x-access-token": login_interface["token"], "Content-Type": "application/json"}

    name_a = f"API前置商品A_{uuid4().hex[:8]}"
    name_b = f"API重复条码B_{uuid4().hex[:8]}"
    barcode_a = str(uuid4().int)[:18]
    material_cleaner(name_a)
    material_cleaner(name_b) 

    # 1. 前置创建商品 A
    time.sleep(2)
    with allure.step("前置创建商品 A"):
        resp_a = requests.post(
        f"{base_url}/jshERP-boot/material/add",
        json=build_material_payload(name_a, barcode_a),
        headers=headers,
        timeout=10,
    )
        assert resp_a.status_code == 200, resp_a.text
        assert resp_a.json()["code"] == 200, resp_a.json()

    with allure.step("新增商品 B 时使用重复条码，断言被拒绝"):
        # 2. 用相同条码新增商品 B，断言被拒绝
        time.sleep(2)
        resp_b = requests.post(
            f"{base_url}/jshERP-boot/material/add",
            json=build_material_payload(name_b, barcode_a),
            headers=headers,
            timeout=10,
        )
        assert resp_b.status_code == 200, resp_b.text
        body_b = resp_b.json()
        assert body_b["code"] == 8000005, body_b
        assert "重复" in body_b["data"]["message"]

    time.sleep(2)
    with allure.step("查询商品 B"):
        q = requests.get(
        f"{base_url}/jshERP-boot/material/list",
        params={"search": json.dumps({"materialParam": name_b}, ensure_ascii=False), "currentPage": 1, "pageSize": 10},
        headers=headers,
        timeout=10,
    )
        assert q.status_code == 200 and q.json()["code"] == 200
        assert [r for r in q.json()["data"]["rows"] if r["name"] == name_b] == []

@allure.feature("商品接口")
@allure.story("新增商品")
@allure.title("TC-MAT-ADD-006：新增商品时 name 超过 100 字符，应返回 301。")
def test_tc_mat_add_006_overlength_name(base_url, login_interface, material_cleaner):
    """TC-MAT-ADD-006：新增商品时 name 超过 100 字符，应返回 301。"""
    headers = {"x-access-token": login_interface["token"], "Content-Type": "application/json"}
    name = f"API超长_{uuid4().hex[:6]}".ljust(101, "a")
    barcode = str(uuid4().int)[:18]
    material_cleaner(name)

    time.sleep(2)
    with allure.step("新增商品"):
        resp = requests.post(
        f"{base_url}/jshERP-boot/material/add",
        json=build_material_payload(name, barcode),
        headers=headers,
        timeout=10,
    )
    
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == 301, body
        assert body["data"]["message"] == "数据写入异常"

    time.sleep(2)
    with allure.step("查询商品"):
        response_list = requests.get(
        f"{base_url}/jshERP-boot/material/list",
        params={"search": json.dumps({"materialParam": barcode}, ensure_ascii=False), "currentPage": 1, "pageSize": 10},
        headers=headers,
        timeout=10)
    assert response_list.status_code == 200,response_list.text
    assert response_list.json()["code"] == 200
    assert response_list.json()["data"]["rows"] == []
    assert response_list.json()["data"]["total"] == 0

@allure.feature("商品接口")
@allure.story("新增商品")
@allure.title("TC-MAT-ADD-019：新增商品时 meList 含2条明细且第2条 barCode 重复-整单回滚")
def test_tc_mat_add_019_with_two_barcode(base_url, login_interface, material_cleaner):
    """TC-MAT-ADD-019：新增商品时 meList含2条明细且第2条barCode与已有商品重复-整单回滚"""
    headers = {"x-access-token": login_interface["token"], "Content-Type": "application/json"}
    name = f"API异常_019_{uuid4().hex[:6]}"
    
    barcode1 = str(uuid4().int)[:18]
    barcode2 = str(uuid4().int)[:18]
    pre_existing_product=build_material_payload(f"API异常_019_前置_{uuid4().hex[:6]}", barcode2)
    material_cleaner(name)
    material_cleaner(pre_existing_product["name"])
    with allure.step("前置创建商品"):
        time.sleep(2)
        response_pre_existing = requests.post(
        f"{base_url}/jshERP-boot/material/add",
        json=pre_existing_product,
        headers=headers,
        timeout=10,
    )
        assert response_pre_existing.status_code == 200, response_pre_existing.text
        assert response_pre_existing.json()["code"] == 200, response_pre_existing.json()

    time.sleep(2)
    with allure.step("新增商品"):
        resp = requests.post(
        f"{base_url}/jshERP-boot/material/add",
        json={
            "name": name,
            "standard": "500ml",
            "unit": "瓶",
            "meList": [
                {"barCode": barcode1, "commodityUnit": "瓶", "sku": ""},
                {"barCode": barcode2, "commodityUnit": "瓶", "sku": ""}
            ],
            "stock": [],
            "sortList": [],
            "meDeleteIdList": [],
        },
        headers=headers,
        timeout=10,
    )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["code"] == 8000005, body
        assert "重复" in body["data"]["message"]

    time.sleep(2)
    with allure.step("查询商品"):
        response_list = requests.get(
        f"{base_url}/jshERP-boot/material/list",
        params={"search": json.dumps({"materialParam": barcode1}, ensure_ascii=False), "currentPage": 1, "pageSize": 10},
        headers=headers,
        timeout=10) 
        assert response_list.status_code == 200,response_list.text
        assert response_list.json()["code"] == 200
        assert response_list.json()["data"]["rows"] == []
        assert response_list.json()["data"]["total"] == 0


    with allure.step("查询商品 B"):
        response_list_pre_existing = requests.get(
        f"{base_url}/jshERP-boot/material/list",
        params={"search": json.dumps({"materialParam": pre_existing_product["name"]}, ensure_ascii=False), "currentPage": 1, "pageSize": 10},
        headers=headers,
        timeout=10)
        assert response_list_pre_existing.status_code == 200,response_list_pre_existing.text
        assert response_list_pre_existing.json()["code"] == 200
        assert any(r["name"] == pre_existing_product["name"] for r in response_list_pre_existing.json()["data"]["rows"])
