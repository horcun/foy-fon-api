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

        # Tüm API yanıtlarını yakala
        async def handle_response(response):
            url = response.url
            if 'tefas.gov.tr/api' in url or 'BindHistory' in url or 'GetFund' in url or 'Bind' in url:
                try:
                    text = await response.text()
                    print(f"\n📡 API: {url}")
                    print(f"   Status: {response.status}")
                    print(f"   İlk 300: {text[:300]}")
                    if not text.strip().startswith('<'):
                        try:
                            data = json.loads(text)
                            rows = data.get('data', [])
                            if rows:
                                print(f"   ✅ {len(rows)} satır!")
                                intercepted.extend(rows)
                        except:
                            pass
                except Exception as e:
                    print(f"   Hata: {e}")

        page.on('response', handle_response)

        print("TEFAS açılıyor...")
        await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx', wait_until='networkidle', timeout=60000)
        print(f"Sayfa: {await page.title()}")
        await asyncio.sleep(3)

        # "Analiz Et" butonuna tıkla
        print("\n'Analiz Et' butonuna tıklanıyor...")
        buttons = await page.query_selector_all('input[type=button], button')
        for btn in buttons:
            val = await btn.get_attribute('value') or await btn.inner_text()
            if 'Analiz' in str(val):
                await btn.click()
                print("Tıklandı!")
                break

        await asyncio.sleep(5)
        print(f"\nYakalanan toplam: {len(intercepted)} satır")

        # Sonuçları kaydet
        fund_latest = {}
        for row in intercepted:
            code = row.get('FONKODU', '')
            if code:
                fund_latest[code] = {
                    'code': code,
                    'name': row.get('FONUNVAN', ''),
                    'price': float(row.get('FIYAT', 0) or 0),
                    'date': row.get('TARIH', ''),
                }

        await browser.close()
        return fund_latest


if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS - Analiz Et Butonu")
    print("=" * 50)

    funds = asyncio.run(fetch_all_funds())
    print(f"\nToplam {len(funds)} fon")

    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': len(funds),
        'funds': funds,
    }

    with open('funds.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print("funds.json kaydedildi!")
    if funds:
        sample = list(funds.values())[0]
        print(f"Örnek: {sample}")
