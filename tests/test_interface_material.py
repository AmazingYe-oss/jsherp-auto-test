"""接口用例：新增商品后查询确认，清理交给 material_cleaner 自动完成。"""

import json
from uuid import uuid4

import requests
import allure

@allure.feature("商品接口")
@allure.story("新增商品")
@allure.title("新增商品后查询确认，清理交给 material_cleaner 自动完成。")
def test_material_crud(base_url, login_interface, material_cleaner):
    token = login_interface["token"]
    headers = {
        "x-access-token": token,
        "Content-Type": "application/json",
    }

    
    name = f"API调研商品_{uuid4().hex[:8]}"
    barcode = str(uuid4().int)[:20]
    material_cleaner(name) 
    with allure.step("构造请求体"):
        
        request_body = {
            "name": name,
            "standard": "500ml",
            "unit": "瓶",
            "meList": [{"barCode": barcode, "commodityUnit": "瓶", "sku": ""}],
            "stock": [],
            "sortList": [],
            "meDeleteIdList": [],
        }
    with allure.step("发送新增请求,并校验响应状态码和响应体"):
        response = requests.post(
            f"{base_url}/jshERP-boot/material/add",
            json=request_body,
            headers=headers,
            timeout=10,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["code"] == 200, body

    with allure.step("发送查询请求,并校验响应状态码和响应体"):
        query = requests.get(
            f"{base_url}/jshERP-boot/material/list",
            params={
                "search": json.dumps({"materialParam": name}, ensure_ascii=False),
                "currentPage": 1,
                "pageSize": 10,
            },
            headers=headers,
            timeout=10,
        )
        assert query.status_code == 200, query.text
        rows = [r for r in query.json()["data"]["rows"] if r["name"] == name]
        assert len(rows) == 1, f"应恰好新增1条，实际{len(rows)}条"
        assert rows[0]["mBarCode"] == barcode
