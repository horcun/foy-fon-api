import asyncio
import json
from datetime import datetime
from playwright.async_api import async_playwright

async def fetch_all_funds():
    all_funds = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-blink-features=AutomationControlled']
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='tr-TR',
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        # TÜM istekleri yakala
        async def handle_response(response):
            url = response.url
            if 'tefas.gov.tr' in url and response.status == 200:
                print(f"  → {response.status} {url[:80]}")

        page.on('response', handle_response)

        print("TEFAS açılıyor...")
        await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx', wait_until='networkidle', timeout=60000)
        await asyncio.sleep(2)

        # Sayfadaki input alanlarını listele
        inputs = await page.query_selector_all('input[type=text], input[type=hidden]')
        print(f"\nInput alanları ({len(inputs)} adet):")
        for inp in inputs[:15]:
            iid = await inp.get_attribute('id') or ''
            iname = await inp.get_attribute('name') or ''
            ival = await inp.get_attribute('value') or ''
            if iid or iname:
                print(f"  id='{iid}' name='{iname}' value='{ival[:30]}'")

        # Fon kodu gir ve analiz et
        print("\nAAK fon kodu giriliyor...")
        try:
            # Fon kodu input'unu bul
            fon_input = await page.query_selector('#MainContent_TextBoxFonKod, input[name*="FonKod"], input[name*="fonkod"]')
            if fon_input:
                await fon_input.fill('AAK')
                print("Fon kodu girildi: AAK")
            else:
                print("Fon kodu input bulunamadı, URL ile deneyelim")
                await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx?fon=AAK', wait_until='networkidle', timeout=60000)
        except Exception as e:
            print(f"Input hatası: {e}")

        await asyncio.sleep(2)

        print("\n'Analiz Et' butonuna tıklanıyor...")
        buttons = await page.query_selector_all('input[type=button], button, input[type=submit]')
        for btn in buttons:
            val = await btn.get_attribute('value') or await btn.inner_text()
            if 'Analiz' in str(val):
                print(f"Tıklanıyor: {val}")
                await btn.click()
                break

        print("\nBekleniyor...")
        await asyncio.sleep(5)

        # Sayfa HTML'inden fiyat çek
        html = await page.content()
        print(f"\nSayfa boyutu: {len(html)} karakter")

        # Fiyat içeren elementleri bul
        price_elements = await page.query_selector_all('[id*="FIYAT"], [id*="Fiyat"], [class*="price"]')
        print(f"Fiyat elementi sayısı: {len(price_elements)}")
        for el in price_elements[:5]:
            eid = await el.get_attribute('id') or ''
            text = await el.inner_text()
            print(f"  id='{eid}': '{text}'")

        await browser.close()
        return all_funds


if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS - Network Keşfi")
    print("=" * 50)

    funds = asyncio.run(fetch_all_funds())

    output = {
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'count': 0,
        'funds': {},
    }

    with open('funds.json', 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print("Bitti.")
