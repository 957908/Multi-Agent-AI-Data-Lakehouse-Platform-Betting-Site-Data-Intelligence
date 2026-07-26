import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto('https://www.10cric247.com/?modalId=cashier', wait_until='networkidle')
        print('URL:', page.url)
        print('Title:', await page.title())
        html = await page.content()
        print('CONTENT-LEN:', len(html))
        selectors = ['.payment-method-item', '.payment-method', '.payment-item', '[data-name]']
        for s in selectors:
            found = await page.query_selector_all(s)
            print(f"{s}: {len(found)}")
        element = await page.query_selector('body')
        if element:
            body = await element.inner_html()
            print('BODY-SNIP:', body[:1000].replace('\n', ' '))
        await browser.close()

asyncio.run(main())
