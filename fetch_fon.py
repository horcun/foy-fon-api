import asyncio
import json
import random
from datetime import datetime, timedelta
from playwright.async_api import async_playwright

async def fetch_all_funds():
    today = datetime.now()
    end_date = today.strftime("%d.%m.%Y")
    start_date = (today - timedelta(days=7)).strftime("%d.%m.%Y")

    all_funds = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--disable-infobars',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--no-first-run',
                '--disable-default-apps',
            ]
        )

        context = await browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            locale='tr-TR',
            timezone_id='Europe/Istanbul',
            viewport={'width': 1366, 'height': 768},
            extra_http_headers={
                'Accept-Language': 'tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
            }
        )

        # Stealth — otomasyon parmak izlerini gizle
        await context.add_init_script("""
            // webdriver gizle
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });

            // Diller
            Object.defineProperty(navigator, 'languages', { get: () => ['tr-TR', 'tr', 'en-US', 'en'] });

            // Platform
            Object.defineProperty(navigator, 'platform', { get: () => 'Win32' });

            // Plugin sayısı (gerçek tarayıcı gibi)
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });

            // Chrome objesi
            window.chrome = { runtime: {} };

            // Permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => (
                parameters.name === 'notifications' ?
                    Promise.resolve({ state: Notification.permission }) :
                    originalQuery(parameters)
            );
        """)

        page = await context.new_page()

        print("TEFAS ana sayfası açılıyor...")
        try:
            await page.goto(
                'https://www.tefas.gov.tr/FonAnaliz.aspx',
                wait_until='networkidle',
                timeout=60000
            )
        except Exception as e:
            print(f"Sayfa yükleme hatası: {e}")

        # Cookie'leri logla
        cookies = await context.cookies()
        cookie_names = [c['name'] for c in cookies]
        print(f"Cookie sayısı: {len(cookies)}")
        print(f"Cookie isimleri: {cookie_names}")

        has_xid = any('xid' in name.lower() for name in cookie_names)
        has_wid = any('wid' in name.lower() for name in cookie_names)
        print(f"XID cookie var mı: {has_xid}")
        print(f"WID cookie var mı: {has_wid}")

        # Akıllı bekleme — WAF challenge tamamlansın
        wait_time = random.uniform(4, 6)
        print(f"{wait_time:.1f} saniye bekleniyor (WAF challenge için)...")
        await asyncio.sleep(wait_time)

        # Sayfa başlığını kontrol et
        title = await page.title()
        print(f"Sayfa başlığı: {title}")

        for fontip in ['YAT', 'EMK', 'BYF']:
            print(f"\n--- {fontip} fonları çekiliyor ---")
            try:
                # Sayfadan JavaScript ile istek at — aynı oturumdan gidiyor
                result = await page.evaluate(f"""
                    async () => {{
                        try {{
                            const res = await fetch('/api/DB/BindHistoryInfo', {{
                                method: 'POST',
                                headers: {{
                                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                                    'X-Requested-With': 'XMLHttpRequest',
                                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                                }},
                                body: 'startdate={start_date}&enddate={end_date}&fontip={fontip}&fonkod='
                            }});
                            const text = await res.text();
                            return {{
                                status: res.status,
                                isHtml: text.trim().startsWith('<'),
                                preview: text.slice(0, 400),
                                body: text
                            }};
                        }} catch(e) {{
                            return {{ error: e.toString() }};
                        }}
                    }}
                """)

                print(f"HTTP Status: {result.get('status')}")
                print(f"HTML mı: {result.get('isHtml')}")
                print(f"Yanıt başlangıcı: {result.get('preview', '')[:300]}")

                if result.get('isHtml'):
                    preview = result.get('preview', '')
                    if 'WAF' in preview or 'Firewall' in preview:
                        print("❌ WAF engeli devam ediyor — JS challenge hala çözülmedi")
                    elif 'Just a moment' in preview:
                        print("❌ Cloudflare challenge — farklı bir koruma katmanı")
                    else:
                        print(f"❌ Beklenmeyen HTML: {preview[:200]}")
                    continue

                body = result.get('body', '')
                if not body:
                    print("Boş yanıt")
                    continue

                data = json.loads(body)
                rows = data.get('data', [])
                print(f"✅ {len(rows)} fon verisi alındı!")

                fund_latest = {}
                for row in rows:
                    code = row.get('FONKODU', '')
                    date = row.get('TARIH', '')
                    if code not in fund_latest or date > fund_latest[code]['date']:
                        fund_latest[code] = {
                            'code': code,
                            'name': row.get('FONUNVAN', ''),
                            'price': float(row.get('FIYAT', 0)),
                            'date': date,
                            'type': fontip,
                        }

                all_funds.update(fund_latest)

                # Fonlar arası insansı bekleme
                await asyncio.sleep(random.uniform(1, 2))

            except Exception as e:
                print(f"❌ {fontip} hata: {type(e).__name__}: {e}")

        await browser.close()

    return all_funds


if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS fon fiyatları çekiliyor (Playwright Stealth)")
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
        print(f"Örnek fon: {sample}")
