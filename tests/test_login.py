import re

from playwright.sync_api import Page, expect


def test_login_success(page: Page, erp_config):
    # 打开页面：page 代表本次测试使用的浏览器标签页。
    page.goto(f"{erp_config['base_url']}/user/login", wait_until="domcontentloaded")

    # 找到输入框并填写内容。
    page.get_by_placeholder("请输入用户名", exact=True).fill(erp_config["username"])
    page.get_by_placeholder("请输入密码", exact=True).fill(erp_config["password"])

    # 找到登录按钮并点击，兼容按钮文字中可能出现的空格。
    page.get_by_role("button", name=re.compile(r"登\s*录")).click()

    # 断言：检查实际结果是否符合预期，而不只是检查点击执行过。
    expect(page).to_have_url(re.compile(r"/dashboard/analysis(?:[?#].*)?$"))
    expect(page.get_by_role("tab", name=re.compile("首页"))).to_be_visible()
