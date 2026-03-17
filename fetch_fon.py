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

        # Tüm network isteklerini yakala
        captured = []
        async def on_response(response):
            if 'tefas' in response.url and response.status == 200:
                captured.append(response.url)

        page.on('response', on_response)

        print("Sayfa yükleniyor...")
        await page.goto('https://www.tefas.gov.tr/FonAnaliz.aspx?fon=AAK', wait_until='domcontentloaded', timeout=30000)

        # 10 saniye bekle — tüm JS yüklensin
        print("10 saniye bekleniyor...")
        await asyncio.sleep(10)

        print(f"\nYakalanan URL'ler ({len(captured)}):")
        for url in captured:
            print(f"  {url[:100]}")

        # Grafik elementinin içeriğine bak
        html = await page.content()

        # Sıfır olmayan sayı dizilerini bul
        nonzero = re.findall(r'\[([^\]]*[1-9][^\]]*)\]', html)
        print(f"\nSıfır olmayan diziler ({len(nonzero)}):")
        for arr in nonzero[:5]:
            if '.' in arr and len(arr) < 200:
                print(f"  {arr[:150]}")

        # Sayfa içindeki tüm sayısal değerleri kontrol et
        # Özellikle fon fiyatı olabilecek 0.001-999 arası değerler
        numbers = re.findall(r'\b(\d+\.\d{3,8})\b', html)
        unique = list(set(numbers))
        print(f"\nSayısal değerler (benzersiz, {len(unique)} adet):")
        print(unique[:20])

        await browser.close()

if __name__ == '__main__':
    asyncio.run(find_price())
    with open('funds.json', 'w') as f:
        json.dump({'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 'count': 0, 'funds': {}}, f)
