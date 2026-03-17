import json
from datetime import datetime, timedelta
from curl_cffi import requests

def fetch_all_funds():
    today = datetime.now()
    end_date = today.strftime("%d.%m.%Y")
    start_date = (today - timedelta(days=7)).strftime("%d.%m.%Y")

    session = requests.Session(impersonate="chrome120")

    # Cookie al
    print("Session başlatılıyor...")
    try:
        session.get(
            'https://www.tefas.gov.tr/FonAnaliz.aspx',
            timeout=30
        )
        print("Session OK")
    except Exception as e:
        print(f"Session hatası: {e}")

    all_funds = {}

    for fontip in ['YAT', 'EMK', 'BYF']:
        print(f"{fontip} çekiliyor...")
        try:
            res = session.post(
                'https://www.tefas.gov.tr/api/DB/BindHistoryInfo',
                data=f'startdate={start_date}&enddate={end_date}&fontip={fontip}&fonkod=',
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'X-Requested-With': 'XMLHttpRequest',
                    'Accept': 'application/json, text/javascript, */*; q=0.01',
                    'Referer': 'https://www.tefas.gov.tr/FonAnaliz.aspx',
                    'Origin': 'https://www.tefas.gov.tr',
                },
                timeout=30
            )

            text = res.text
            print(f"  Status: {res.status_code}")
            print(f"  Yanıt: {text[:200]}")

            if text.strip().startswith('<'):
                print(f"  HTML döndü")
                continue

            data = res.json()
            rows = data.get('data', [])
            print(f"  ✅ {len(rows)} fon!")

            for row in rows:
                code = row.get('FONKODU', '')
                date = row.get('TARIH', '')
                if code not in all_funds or date > all_funds[code]['date']:
                    all_funds[code] = {
                        'code': code,
                        'name': row.get('FONUNVAN', ''),
                        'price': float(row.get('FIYAT', 0) or 0),
                        'date': date,
                    }

        except Exception as e:
            print(f"  Hata: {e}")

    return all_funds


if __name__ == '__main__':
    print("=" * 50)
    print("TEFAS - curl_cffi Chrome TLS")
    print("=" * 50)

    funds = fetch_all_funds()
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
