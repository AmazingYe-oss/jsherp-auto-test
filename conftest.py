import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from playwright.sync_api import Page, expect
import re

from common.common_tools import cleanup_product
import requests
import time
import hashlib
import json
load_dotenv(Path(__file__).parent / ".env", override=False)



@pytest.fixture
def erp_config():
    """从本地配置读取地址和练习账号，避免在用例中写密码。"""
    username = os.getenv("ERP_USERNAME")
    password = os.getenv("ERP_PASSWORD")
    if not username or not password:
        pytest.fail("请在本地 .env 中设置 ERP_USERNAME 和 ERP_PASSWORD")
    return {
        "base_url": os.getenv("ERP_BASE_URL", "http://127.0.0.1:18090").rstrip("/"),
        "username": username,
        "password": password,
    }


@pytest.fixture
def login(page: Page, erp_config):
    """声明依赖本 fixture 的用例会自动先登录，无需在用例内再次调用。"""
    page.goto(f"{erp_config['base_url']}/user/login", wait_until="domcontentloaded")
    page.get_by_placeholder("请输入用户名", exact=True).fill(erp_config["username"])
    page.get_by_placeholder("请输入密码", exact=True).fill(erp_config["password"])
    page.get_by_role("button", name=re.compile(r"登\s*录")).click()
    expect(page).to_have_url(re.compile(r"/dashboard/analysis(?:[?#].*)?$"))



@pytest.fixture
def cleanup_products(page, erp_config):
    product_names = []

    yield product_names  # 把列表交给用例，暂停在这里

    
    for name in product_names:
        cleanup_product(page, erp_config, name)


@pytest.fixture
def login_interface(erp_config):
    request_body = {
        "loginName": erp_config["username"],
        "password": hashlib.md5(erp_config["password"].encode()).hexdigest(),
        "uuid": "7cc67149ce794c1ea1a24288b1e257ac"
    }
    response = requests.post(f"{erp_config['base_url']}/jshERP-boot/user/login", json=request_body)
    
    assert response.status_code == 200
    assert response.json()['code'] == 200
    assert response.json()['data']['user']['loginName'] == request_body['loginName']
    assert response.json()['data']['user']['status'] == 0
    assert isinstance(response.json()['data']['token'], str)
    assert response.json()['data']['token'] != ""
    return response.json()['data']

@pytest.fixture(scope="session")
def base_url():
    return os.getenv("ERP_BASE_URL", "http://127.0.0.1:18090").rstrip("/")


@pytest.fixture
def material_cleaner(base_url, login_interface):
    """用例创建的商品在此登记名称，测试结束后自动删除并复查。

    登记名称即可，teardown 里自动：查询id -> deleteBatch删除 -> 重新查询确认不存在。
    用例失败也会清理（yield 结构保证），漏删会让 teardown 断言失败而暴露。
    """
    token = login_interface["token"]
    headers = {
        "x-access-token": token,
        "Content-Type": "application/json",
    }

    def query_rows(product_name):
        """按名称查询，返回精确匹配的行（列表）。"""
        response = requests.get(
            f"{base_url}/jshERP-boot/material/list",
            params={
                "search": json.dumps({"materialParam": product_name}, ensure_ascii=False),
                "currentPage": 1,
                "pageSize": 10,
            },
            headers=headers,
            timeout=10,
        )
        if response.status_code != 200 or response.json().get("code") != 200:
            return []
        return [r for r in response.json()["data"]["rows"] if r["name"] == product_name]

    registered = []

    def register(product_name):
        """登记一个待清理的商品名称（可重复调用登记多个）。"""
        registered.append(product_name)

    yield register

    for product_name in registered:
        rows = query_rows(product_name)
        if not rows:
            continue  
        ids = ",".join(str(r["id"]) for r in rows)
        time.sleep(2)  
        delete_response = requests.delete(
            f"{base_url}/jshERP-boot/material/deleteBatch",
            params={"ids": ids},
            headers=headers,
            timeout=10,
        )
        assert delete_response.status_code == 200, delete_response.text
        assert delete_response.json()["code"] == 200, delete_response.text
        # 重新查询确认已删除
        remaining = query_rows(product_name)
        assert not remaining, f"清理后仍存在：{product_name} -> {remaining}"
        print(f"已自动清理商品：{product_name}")


import pymysql

@pytest.fixture
def db_conn():
    """读取 .env 配置建立 MySQL 连接，用完自动关闭。"""
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "3306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME", "jsh_erp"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,  # 查询结果按字典返回，方便按列名断言
        autocommit=True,                         # 避免长连接事务隔离级别导致查不到接口刚写入的新数据！
    )
    try:
        yield conn
    finally:
        conn.close()