import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def fetch_all_funds():
    all_funds = {}
    intercepted = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='tr-TR',
            timezone_id='Europe/Istanbul',
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        # API yanıtlarını yakala
        async def handle_response(response):
            if 'BindHistoryInfo' in response.url or 'BindFundReturn' in response.url or 'GetAllFund' in response.url:
                try:
                    text = await response.text()
                    print(f"API yakalandı: {response.url}")
                    print(f"İlk 200 karakter: {text[:200]}")
                    if not text.strip().startswith('<'):
                        data = json.loads(text)
                        rows = data.get('data', [])
                        print(f"✅ {len(rows)} satır!")
                        intercepted.extend(rows)
                except Exception as e:
                    print(f"Hata: {e}")

        page.on('response', handle_response)

        # Fon Analiz sayfasına git
        print("Fon Analiz sayfasına gidiliyor...")
        await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx', wait_until='networkidle', timeout=60000)
        print(f"Sayfa: {await page.title()}")
        await asyncio.sleep(3)

        # Sayfadaki tüm butonları listele
        buttons = await page.query_selector_all('input[type=button], button, input[type=submit]')
        print(f"Buton sayısı: {len(buttons)}")
        for i, btn in enumerate(buttons[:10]):
            val = await btn.get_attribute('value') or await btn.inner_text()
            bid = await btn.get_attribute('id') or ''
            print(f"  Buton {i}: '{val}' id='{bid}'")

        # Sayfadaki select/dropdown'ları listele
        selects = await page.query_selector_all('select')
        print(f"Select sayısı: {len(selects)}")
        for i, sel in enumerate(selects[:5]):
            sid = await sel.get_attribute('id') or ''
            print(f"  Select {i}: id='{sid}'")

        await asyncio.sleep(3)
        print(f"Yakalanan: {len(intercepted)} satır")

        await browser.close()

    return all_funds, intercepted


if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS - Sayfa Keşfi")
    print("=" * 50)

    funds, intercepted = asyncio.run(fetch_all_funds())
    print(f"\nYakalanan toplam: {len(intercepted)}")

    # Boş json kaydet
    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(intercepted),
        'funds': {},
        'raw_sample': intercepted[:2] if intercepted else []
    }

    with open('funds.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("funds.json kaydedildi!")
