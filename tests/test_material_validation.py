import re

from playwright.sync_api import Page, expect

from uuid import uuid4

import time
from common.common_tools import gen_product_name






def test_material_name_required(page: Page, erp_config, login):
    """UI-M-007：名称为空、单位有效时，保存应显示名称必填提示。"""
    page.goto(f"{erp_config['base_url']}/material/material", wait_until="domcontentloaded")
    page.get_by_role("button", name=re.compile(r"新增$")).click()

    guide = page.get_by_role("dialog").filter(has_text="名称必填，可以重复")
    guide.get_by_role("button", name="×", exact=True).click()
    expect(guide).not_to_be_visible()

    dialog = page.get_by_role("dialog", name=re.compile(r"^新增"))
    expect(dialog).to_be_visible()
    name_input = dialog.get_by_placeholder("请输入名称", exact=True)
    unit_input = dialog.get_by_placeholder("输入单位", exact=True)

    name_input.fill("")
    unit_input.fill("个")
    expect(name_input).to_have_value("")
    expect(unit_input).to_have_value("个")
    dialog.get_by_role("button", name="保存（Ctrl+S）", exact=True).click()

   
    expect(dialog.get_by_text("请输入名称!", exact=True)).to_be_visible()
    expect(dialog.get_by_text("请输入单位!", exact=True)).not_to_be_visible()
    expect(dialog).to_be_visible()

def test_material_unit_required(page: Page, erp_config, login):
    """UI-M-005：名称有效、单位为空时，保存应显示单位必填提示。"""
    page.goto(f"{erp_config['base_url']}/material/material", wait_until="domcontentloaded")
    page.get_by_role("button", name=re.compile(r"新增$")).click()

    guide = page.get_by_role("dialog").filter(has_text="名称必填，可以重复")
    guide.get_by_role("button", name="×", exact=True).click()
    expect(guide).not_to_be_visible()

    dialog = page.get_by_role("dialog", name=re.compile(r"^新增"))
    expect(dialog).to_be_visible()
    name_input = dialog.get_by_placeholder("请输入名称", exact=True)
    unit_input = dialog.get_by_placeholder("输入单位", exact=True)

    name_input.fill("UI练习商品_002")
    unit_input.fill("")
    expect(name_input).to_have_value("UI练习商品_002")
    expect(unit_input).to_have_value("")
    dialog.get_by_role("button", name="保存（Ctrl+S）", exact=True).click()
    expect(dialog.get_by_text("请输入名称!", exact=True)).not_to_be_visible()
    expect(dialog.get_by_text("请输入单位!", exact=True)).to_be_visible()
    expect(dialog).to_be_visible()


def test_material_gen_query_product(page: Page, erp_config, login,cleanup_products):
    """UI-M-008：新增商品后，查询应能找到该商品。"""
    page.goto(f"{erp_config['base_url']}/material/material", wait_until="domcontentloaded")
    page.get_by_role("button", name=re.compile(r"新增$")).click()

    guide = page.get_by_role("dialog").filter(has_text="名称必填，可以重复")
    guide.get_by_role("button", name="×", exact=True).click()
    expect(guide).not_to_be_visible()

    dialog = page.get_by_role("dialog", name=re.compile(r"^新增"))
    expect(dialog).to_be_visible()
    name_input = dialog.get_by_placeholder("请输入名称", exact=True)
    unit_input = dialog.get_by_placeholder("输入单位", exact=True)

    product_name = gen_product_name()
    
    name_input.fill(product_name)
    unit_input.fill("个")
    expect(name_input).to_have_value(product_name)
    expect(unit_input).to_have_value("个")
    dialog.get_by_role("button", name="保存（Ctrl+S）", exact=True).click()
    expect(dialog).not_to_be_visible()
    cleanup_products.append(product_name)

    # 仅包住已确认创建成功之后的检查；finally不吞掉原来的断言失败。
   
    query_input = page.get_by_placeholder(re.compile(r"^请输入条码"))
    query_input.fill(product_name)
    with page.expect_response("**/jshERP-boot/material/list?*") as query_response:
        page.get_by_role("button", name=re.compile(r"查\s*询$")).click()
    assert query_response.value.ok


    expect(
    page.get_by_role("cell", name=product_name, exact=True)
).to_be_visible()


        # 找到包含本次商品名称的那一行
    product_row = page.get_by_role("row").filter(
        has=page.get_by_role("cell", name=product_name, exact=True)
    )

    # 只在这一行里检查单位
    expect(
        product_row.get_by_role("cell", name="个", exact=True)
    ).to_be_visible()



def test_material_edit_standard(page: Page, erp_config, login,cleanup_products):
    """UI-M-009：编辑商品规格后，重新查询显示新规格，并收尾本次数据。"""
    page.goto(f"{erp_config['base_url']}/material/material", wait_until="domcontentloaded")
    page.get_by_role("button", name=re.compile(r"新增$")).click()

    guide = page.get_by_role("dialog").filter(has_text="名称必填，可以重复")
    guide.get_by_role("button", name="×", exact=True).click()
    expect(guide).not_to_be_visible()

    dialog = page.get_by_role("dialog", name=re.compile(r"^新增"))
    expect(dialog).to_be_visible()
    name_input = dialog.get_by_placeholder("请输入名称", exact=True)
    unit_input = dialog.get_by_placeholder("输入单位", exact=True)

    product_name = gen_product_name()
    
    name_input.fill(product_name)
    unit_input.fill("个")
    expect(name_input).to_have_value(product_name)
    expect(unit_input).to_have_value("个")
    dialog.get_by_placeholder("请输入规格", exact=True).fill("500ml")
    dialog.get_by_role("button", name="保存（Ctrl+S）", exact=True).click()
    expect(dialog).not_to_be_visible()
    cleanup_products.append(product_name)
    # 已确认创建成功，开始执行编辑检查。
    
    query_input = page.get_by_placeholder(re.compile(r"^请输入条码"))
    query_input.fill(product_name)
    with page.expect_response("**/jshERP-boot/material/list?*") as query_response:
        page.get_by_role("button", name=re.compile(r"查\s*询$")).click()
    assert query_response.value.ok


    expect(
    page.get_by_role("cell", name=product_name, exact=True)
).to_be_visible()


        # 找到包含本次商品名称的那一行
    product_row = page.get_by_role("row").filter(
        has=page.get_by_role("cell", name=product_name, exact=True)
    )

    # 只在这一行里检查单位
    expect(
        product_row.get_by_role("cell", name="个", exact=True)
    ).to_be_visible()

        # 确认编辑前的规格
    expect(
        product_row.get_by_role("cell", name="500ml", exact=True)
    ).to_be_visible()

    # 点击本次商品所在行的编辑链接
    product_row.get_by_text("编辑", exact=True).click()

    edit_dialog = page.get_by_role("dialog", name=re.compile(r"^编辑"))
    expect(edit_dialog).to_be_visible()

    # 修改规格并保存
    edit_dialog.get_by_placeholder("请输入规格", exact=True).fill("750ml")
    # ERP-001：新增与编辑同属商品操作，避免同秒频控清除登录状态。
    time.sleep(2)
    edit_dialog.get_by_role(
        "button", name="保存（Ctrl+S）", exact=True
    ).click()
    expect(edit_dialog).not_to_be_visible()

    # 再次查询，等待本次查询响应
    query_input.fill(product_name)
    with page.expect_response("**/jshERP-boot/material/list?*") as response:
        page.get_by_role("button", name=re.compile(r"查\s*询$")).click()
    assert response.value.ok

    # 检查同一商品的新规格与原单位
    expect(
        product_row.get_by_role("cell", name="750ml", exact=True)
    ).to_be_visible()
    expect(
        product_row.get_by_role("cell", name="个", exact=True)
    ).to_be_visible()

