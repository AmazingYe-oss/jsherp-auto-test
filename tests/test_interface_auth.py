import json
import time
import requests
import hashlib
from uuid import uuid4
import allure

@allure.feature("接口鉴权")
@allure.story("用户登录")
@allure.title("不传 x-access-token 访问业务接口，应被拦截")
def test_material_list_without_token(base_url):
    """鉴权异常：不传 x-access-token 访问业务接口，应被拦截。"""
    with allure.step("发送请求,并校验响应状态码和响应体"):
        response = requests.get(
        f"{base_url}/jshERP-boot/material/list",
        params={"search": json.dumps({"materialParam": ""}), "currentPage": 1, "pageSize": 10},
        timeout=10,
    )
        assert response.status_code == 500, response.text
        assert response.text == "loginOut"

@allure.feature("接口鉴权")
@allure.story("用户登录")
@allure.title("传无效 x-access-token 访问业务接口，应被拦截")
def test_material_list_with_invalid_token(base_url):
    """鉴权异常：传无效 x-access-token 访问业务接口，应被拦截。"""
    headers = {"x-access-token": "invalid_token"}
    with allure.step("发送请求,并校验响应状态码和响应体"):
        response = requests.get(
        f"{base_url}/jshERP-boot/material/list",
        params={"search": json.dumps({"materialParam": ""}), "currentPage": 1, "pageSize": 10},
        headers=headers,
        timeout=10,
    )
    assert response.status_code == 500, response.text
    assert response.text == "loginOut"

@allure.feature("接口鉴权")
@allure.story("用户登录")
@allure.title("传过期 x-access-token 访问业务接口，应被拦截")
def test_material_list_with_expired_token(base_url, erp_config):
    """鉴权异常：传过期 x-access-token 访问业务接口，应被拦截。"""
    ##登录
    with allure.step("构造登录请求体"):
        request_body = {
            "loginName": erp_config["username"],
            "password": hashlib.md5(erp_config["password"].encode()).hexdigest(),
            "uuid": uuid4().hex
        }
    with allure.step("发送登录请求,并校验响应状态码和响应体"):
        response_login = requests.post(f"{erp_config['base_url']}/jshERP-boot/user/login", json=request_body)
        assert response_login.status_code == 200, response_login.text
        assert response_login.json()['code'] == 200
        assert response_login.json()['data']['user']['loginName'] == request_body['loginName']
        assert response_login.json()['data']['user']['status'] == 0
    assert isinstance(response_login.json()['data']['token'], str)
    assert response_login.json()['data']['token'] != ""

    #查询
    token = response_login.json().get("data", {}).get("token")
    headers = {"x-access-token": token}
    time.sleep(2)  
    with allure.step("发送查询请求,并校验响应状态码和响应体"):
        response_list=requests.get(
        f"{base_url}/jshERP-boot/material/list",
        params={"search": json.dumps({"materialParam": ""}), "currentPage": 1, "pageSize": 10},
        headers=headers,
        timeout=10,
    )
    with allure.step("校验查询响应状态码和响应体"):
        assert response_list.status_code == 200, response_list.text
        assert response_list.json()["code"] == 200
        assert "rows" in response_list.json()["data"]

    #登出
    with allure.step("发送登出请求,并校验响应状态码和响应体"):
        time.sleep(2)
        response_login_out = requests.get(
            f"{base_url}/jshERP-boot/user/logout",
            headers=headers,
            timeout=10,
        )
        assert response_login_out.status_code == 200, response_login_out.text
        assert response_login_out.json()["code"] == 400
        assert response_login_out.json()["data"] is None
    with allure.step("登出后再次查询商品列表，校验原 token 已失效"):
        time.sleep(2)
        response_list_after_logout = requests.get(
            f"{base_url}/jshERP-boot/material/list",
            params={"search": json.dumps({"materialParam": ""}), "currentPage": 1, "pageSize": 10},
            headers=headers,
            timeout=10,
        )
    with allure.step("校验查询响应状态码和响应体"):
        assert response_list_after_logout.status_code == 500, response_list_after_logout.text
        assert response_list_after_logout.text == "loginOut"    
