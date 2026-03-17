import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

async def find_price():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='tr-TR',
        )
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => undefined });")
        page = await context.new_page()

        await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx?fon=AAK', wait_until='networkidle', timeout=30000)
        await asyncio.sleep(2)

        html = await page.content()

        # "fiyat" kelimesinin etrafındaki 200 karakteri bul
        for match in re.finditer(r'.{0,100}[Ff]iyat.{0,100}', html):
            snippet = match.group()
            if any(c.isdigit() for c in snippet):
                print(f"FIYAT BULUNAN: {snippet[:200]}")
                print("---")

        # Tüm span elementlerini değerleriyle göster
        print("\n=== SPAN ELEMENTLERI ===")
        spans = await page.query_selector_all('span, td, div')
        for el in spans:
            try:
                eid = await el.get_attribute('id') or ''
                text = (await el.inner_text()).strip()
                # Kısa ve sayı içeren elementler
                if eid and len(text) < 50 and any(c.isdigit() for c in text) and '.' in text:
                    print(f"id='{eid}': '{text}'")
            except:
                pass

        await browser.close()

if __name__ == '__main__':
    asyncio.run(find_price())
    # Boş json kaydet
    with open('funds.json', 'w') as f:
        json.dump({'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'count': 0, 'funds': {}}, f)
