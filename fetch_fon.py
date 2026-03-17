import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

async def find_price():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--disable-accelerated-2d-canvas',
                '--no-first-run',
                '--no-zygote',
                '--single-process',
                '--disable-gpu',
            ]
        )
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
            locale='tr-TR',
            timezone_id='Europe/Istanbul',
            viewport={'width': 390, 'height': 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'platform', { get: () => 'iPhone' });
            Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr'] });
            delete window.__playwright;
            delete window.__pwInitScripts;
        """)

        page = await context.new_page()

        captured_api = []
        async def on_response(response):
            if 'BindHistoryInfo' in response.url or 'api/DB' in response.url:
                try:
                    text = await response.text()
                    print(f"\n🎯 API YAKALANDI: {response.url}")
                    print(f"   {text[:300]}")
                    if not text.strip().startswith('<'):
                        captured_api.append(json.loads(text))
                except:
                    pass

        page.on('response', on_response)

        print("iPhone modunda TEFAS açılıyor...")
        await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx?fon=AAK', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(8)

        print(f"\nYakalanan API: {len(captured_api)}")

        # Tüm yakalanan veriyi işle
        all_funds = {}
        for data in captured_api:
            rows = data.get('data', [])
            for row in rows:
                code = row.get('FONKODU', '')
                if code:
                    all_funds[code] = {
                        'code': code,
                        'name': row.get('FONUNVAN', ''),
                        'price': float(row.get('FIYAT', 0) or 0),
                        'date': row.get('TARIH', ''),
                    }

        await browser.close()
        return all_funds

if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS - iPhone Modu")
    print("=" * 50)

    funds = asyncio.run(find_price())
    print(f"\nToplam {len(funds)} fon")

    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(funds),
        'funds': funds,
    }

    with open('funds.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("Bitti!")
    if funds:
        for k, v in list(funds.items())[:3]:
            print(f"  {k}: {v}")
