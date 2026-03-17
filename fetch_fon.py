import asyncio
import json
import re
from datetime import datetime
from playwright.async_api import async_playwright

FUND_CODES = [
    'AAK', 'AAL', 'AAS', 'AAV', 'ABU', 'ACC', 'ACT', 'ADA', 'ADB', 'ADG',
    'ADK', 'ADL', 'ADN', 'ADP', 'ADS', 'ADT', 'AFT', 'AFV', 'AGB', 'AGC',
    'AGD', 'AGE', 'AGF', 'AGH', 'AGI', 'AGJ', 'AGK', 'AGL', 'AGM', 'AGN',
    'TKF', 'MAC', 'GAF', 'YAC', 'HBY', 'IPB', 'TTE', 'GBF',
]

async def fetch_fund_price(page, code):
    try:
        await page.goto(
            f'https://www.tefas.gov.tr/FonAnaliz.aspx?fon={code}',
            wait_until='networkidle',
            timeout=30000
        )
        await asyncio.sleep(1)

        html = await page.content()

        # Fiyat için çeşitli pattern'lar dene
        patterns = [
            r'FIYAT["\s:]+([0-9]+[.,][0-9]+)',
            r'"fiyat"\s*:\s*"?([0-9]+[.,][0-9]+)"?',
            r'pay\s+fiyat[^0-9]*([0-9]+[.,][0-9]+)',
            r'birim[^0-9]*([0-9]+[.,][0-9]+)',
        ]

        # Sayfa başlığından fon adını al
        title = await page.title()

        # Tüm sayı benzeri değerleri bul
        # Fon fiyatı genellikle küçük bir ondalık sayıdır
        price_candidates = re.findall(r'\b([0-9]{1,4}[.,][0-9]{4,8})\b', html)

        # Fon adını bul
        name_match = re.search(r'<span[^>]*id="[^"]*FonUnvan[^"]*"[^>]*>([^<]+)</span>', html)
        if not name_match:
            name_match = re.search(r'<h1[^>]*>([^<]+)</h1>', html)
        name = name_match.group(1).strip() if name_match else code

        # JavaScript değişkenlerinden fiyat çek
        js_price = re.search(r'var\s+fonFiyat\s*=\s*["\']?([0-9]+[.,][0-9]+)', html)
        if not js_price:
            js_price = re.search(r'"FIYAT"\s*:\s*"([0-9]+[.,][0-9]+)"', html)
        if not js_price:
            js_price = re.search(r'fiyat["\s:]+([0-9]+[.,][0-9]+)', html, re.IGNORECASE)

        price = None
        if js_price:
            price = float(js_price.group(1).replace(',', '.'))
        elif price_candidates:
            # En makul fiyatı seç (0.001 - 9999 arası)
            for p in price_candidates:
                val = float(p.replace(',', '.'))
                if 0.001 < val < 9999:
                    price = val
                    break

        print(f"  {code}: fiyat={price}, aday sayısı={len(price_candidates)}, ilk 3={price_candidates[:3] if price_candidates else []}")

        if price:
            return {
                'code': code,
                'name': name,
                'price': price,
                'date': datetime.now().strftime('%Y-%m-%d'),
            }
    except Exception as e:
        print(f"  {code} hata: {e}")
    return None


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

        # Önce AAK ile test et
        print("AAK test ediliyor...")
        result = await fetch_fund_price(page, 'AAK')
        print(f"AAK sonucu: {result}")

        if result:
            print("\n✅ Çalışıyor! Diğer fonlar çekiliyor...")
            all_funds['AAK'] = result
            for code in FUND_CODES[1:10]:  # İlk 10 fonu test et
                r = await fetch_fund_price(page, code)
                if r:
                    all_funds[r['code']] = r
                await asyncio.sleep(0.5)
        else:
            print("❌ AAK çalışmadı")

        await browser.close()

    return all_funds


if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS - HTML Scraping")
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
        for k, v in list(funds.items())[:3]:
            print(f"  {k}: {v}")
