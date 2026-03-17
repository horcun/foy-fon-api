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
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='tr-TR',
            timezone_id='Europe/Istanbul',
            viewport={'width': 1366, 'height': 768},
        )

        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr'] });
            window.chrome = { runtime: {} };
        """)

        page = await context.new_page()

        # TEFAS'ın kendi API çağrılarını yakala
        async def handle_response(response):
            if 'BindHistoryInfo' in response.url:
                try:
                    text = await response.text()
                    if not text.strip().startswith('<'):
                        data = json.loads(text)
                        rows = data.get('data', [])
                        print(f"✅ API yanıtı yakalandı! {len(rows)} fon")
                        intercepted.extend(rows)
                    else:
                        print(f"❌ API HTML döndü: {text[:100]}")
                except Exception as e:
                    print(f"Yakalama hatası: {e}")

        page.on('response', handle_response)

        # Sayfa yükle
        print("TEFAS açılıyor...")
        await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx', wait_until='networkidle', timeout=60000)
        print(f"Sayfa yüklendi: {await page.title()}")

        await asyncio.sleep(3)

        # TEFAS'ın arama kutusunu kullan — gerçek kullanıcı gibi
        # Fon karşılaştırma sayfasına git — tüm fonları listeler
        print("Fon karşılaştırma sayfasına gidiliyor...")
        await page.goto('https://www.tefas.gov.tr/FonKarsilastirma.aspx', wait_until='networkidle', timeout=60000)
        print(f"Karşılaştırma sayfası: {await page.title()}")

        await asyncio.sleep(5)

        print(f"Yakalanan toplam satır: {len(intercepted)}")

        # Yakalanan verilerden fon fiyatlarını çıkar
        for row in intercepted:
            code = row.get('FONKODU', '')
            date = row.get('TARIH', '')
            if code and code not in all_funds:
                all_funds[code] = {
                    'code': code,
                    'name': row.get('FONUNVAN', ''),
                    'price': float(row.get('FIYAT', 0) or 0),
                    'date': date,
                }

        await browser.close()

    return all_funds


if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS - Intercept Yöntemi")
    print("=" * 50)

    funds = asyncio.run(fetch_all_funds())
    print(f"\nToplam {len(funds)} fon bulundu")

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
