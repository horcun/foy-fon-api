import requests
import json
from datetime import datetime, timedelta

def fetch_all_funds():
    today = datetime.now()
    end_date = today.strftime("%d.%m.%Y")
    start_date = (today - timedelta(days=7)).strftime("%d.%m.%Y")

    headers = {
        'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Accept-Language': 'tr-TR,tr;q=0.9',
        'Referer': 'https://www.tefas.gov.tr/FonAnaliz.aspx',
        'Origin': 'https://www.tefas.gov.tr',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    }

    # Önce session cookie al
    session = requests.Session()
    try:
        session.get('https://www.tefas.gov.tr/FonAnaliz.aspx', headers={
            'User-Agent': headers['User-Agent'],
            'Accept': 'text/html',
        }, timeout=30)
        print(f"Session cookies: {dict(session.cookies)}")
    except Exception as e:
        print(f"Session alınamadı: {e}")

    all_funds = {}

    for fontip in ['YAT', 'EMK', 'BYF']:
        print(f"{fontip} fonları çekiliyor...")
        try:
            response = session.post(
                'https://www.tefas.gov.tr/api/DB/BindHistoryInfo',
                headers=headers,
                data={
                    'startdate': start_date,
                    'enddate': end_date,
                    'fontip': fontip,
                    'fonkod': '',  # Boş bırakınca tüm fonları döndürür
                },
                timeout=30
            )

            text = response.text
            print(f"{fontip} yanıt ({response.status_code}): {text[:200]}")

            if text.strip().startswith('<'):
                print(f"{fontip} HTML döndü, atlanıyor")
                continue

            data = response.json()
            rows = data.get('data', [])
            print(f"{fontip}: {len(rows)} fon bulundu")

            # Her fon için en son fiyatı al
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

        except Exception as e:
            print(f"{fontip} hata: {e}")

    return all_funds

if __name__ == '__main__':
    print("TEFAS fon fiyatları çekiliyor...")
    funds = fetch_all_funds()
    print(f"Toplam {len(funds)} fon bulundu")

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
