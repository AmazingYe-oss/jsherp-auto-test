import hashlib
import json
from uuid import uuid4

import allure
import requests


@allure.feature("认证与基础查询")
@allure.story("用户登录")
@allure.title("正例：正确账号密码（MD5小写）登录成功并返回 token")
def test_login(erp_config):
    with allure.step("1. 构造登录请求体（从 .env 读取配置并计算 MD5）"):
        request_body = {
            "loginName": erp_config["username"],
            "password": hashlib.md5(erp_config["password"].encode()).hexdigest(),
            "uuid": uuid4().hex,
        }

    with allure.step("2. 发送 POST /user/login 并校验用户状态与 token"):
        response = requests.post(
            f"{erp_config['base_url']}/jshERP-boot/user/login",
            json=request_body,
            timeout=10,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["code"] == 200, body
        assert body["data"]["user"]["loginName"] == request_body["loginName"]
        assert body["data"]["user"]["status"] == 0
        assert isinstance(body["data"]["token"], str)
        assert body["data"]["token"] != ""


@allure.feature("认证与基础查询")
@allure.story("商品列表只读查询")
@allure.title("正例：登录后携带 token 查询商品列表并校验字段结构")
def test_login_and_list(base_url, login_interface):
    with allure.step("1. 组装鉴权请求头与分页查询参数"):
        token = login_interface["token"]
        headers = {
            "x-access-token": token,
            "Content-Type": "application/json",
        }
        search_dict = {"materialParam": "API调研商品_001"}
        params = {
            "search": json.dumps(search_dict, ensure_ascii=False),
            "column": "createTime",
            "order": "desc",
            "currentPage": 1,
            "pageSize": 10,
        }

    with allure.step("2. 发送 GET /material/list 并断言业务码及行字段"):
        response = requests.get(
            f"{base_url}/jshERP-boot/material/list",
            params=params,
            headers=headers,
            timeout=10,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["code"] == 200, data
        assert data["data"]["total"] >= 0

        if data["data"]["total"] > 0:
            material = data["data"]["rows"][0]
            assert material["name"] == search_dict["materialParam"]
            assert isinstance(material["id"], int)
            assert material["id"] > 0
            assert isinstance(material["name"], str)
            assert isinstance(material["enabled"], bool)
            assert isinstance(material["tenantId"], int)
            assert material["deleteFlag"] == "0"
            assert material["stock"] >= 0
            assert material["initialStock"] >= 0
            assert isinstance(material["mBarCode"], str)
            assert material["unit"] == "个"
            assert material["attribute"] == "{}"