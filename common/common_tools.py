import re
import time
from playwright.sync_api import Page, expect
from uuid import uuid4

def gen_product_name():
    """生成随机商品名称，避免重复。"""
    return f"UI练习商品_{uuid4().hex[:8]}"


def cleanup_product(page: Page, erp_config, product_name):
    """删除本次创建的单个商品，并重新查询确认不存在；异常不隐藏。"""
    # ERP-001：避开同秒商品操作频控，不是等待页面加载。
    time.sleep(2)
    page.goto(f"{erp_config['base_url']}/material/material", wait_until="domcontentloaded")
    expect(page).to_have_url(re.compile(r"/material/material(?:[?#].*)?$"))

    query_input = page.get_by_placeholder(re.compile(r"^请输入条码"))
    query_input.fill(product_name)
    with page.expect_response("**/jshERP-boot/material/list?*") as query_response:
        page.get_by_role("button", name=re.compile(r"查\s*询$")).click()
    assert query_response.value.ok

    product_row = page.get_by_role("row").filter(
        has=page.get_by_role("cell", name=product_name, exact=True)
    )
    expect(product_row).to_have_count(1)
    product_row.get_by_role("checkbox").check()
    expect(product_row.get_by_role("checkbox")).to_be_checked()
    page.get_by_role("button", name=re.compile(r"删\s*除$")).click()

    delete_dialog = page.get_by_role("dialog").filter(
        has_text="是否删除选中数据?"
    )
    expect(delete_dialog).to_be_visible()
    with page.expect_response("**/jshERP-boot/material/deleteBatch?*") as delete_response:
        delete_dialog.get_by_role("button", name=re.compile(r"确\s*定$")).click()
    assert delete_response.value.ok
    assert delete_response.value.json()["code"] == 200
    expect(delete_dialog).not_to_be_visible()

    query_input.fill(product_name)
    with page.expect_response("**/jshERP-boot/material/list?*") as query_response:
        page.get_by_role("button", name=re.compile(r"查\s*询$")).click()
    assert query_response.value.ok
    expect(page.get_by_role("cell", name=product_name, exact=True)).to_have_count(0)
    print(f"已清理本次商品：{product_name}（重新查询无匹配记录）")