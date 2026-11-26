import json, urllib.request, time
codes = ['2409','3056','3231','2324','00891','1434','2535','9945','2812','00940','00948B','0050','2317','00981A','00403A','00400A','2308','2383']
out = {}
for c in codes:
    url = f'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockDividend&data_id={c}&start_date=2020-01-01&end_date=2026-12-31'
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r:
                d = json.load(r); break
        except Exception as e:
            print('ERR', c, e); time.sleep(3); d = {}
    rows = d.get('data') or []
    out[c] = [{k: x.get(k) for k in ('year','CashEarningsDistribution','CashStatutorySurplus','StockEarningsDistribution','StockStatutorySurplus','CashExDividendTradingDate','StockExDividendTradingDate','CashDividendPaymentDate','date')} for x in rows]
    print(c, d.get('msg'), len(rows))
    time.sleep(1)
print('JSON>>>' + json.dumps(out, ensure_ascii=False) + '<<<JSON')
