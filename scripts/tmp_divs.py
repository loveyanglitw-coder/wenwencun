import json, urllib.request, time
codes = ['00400A','00403A','0050','00679B','00878','00881','00940','00948B','00981A','1301','2308','2368','2409','2812','2897','3037','3056','3162','3231','3260','3264','5289','5309','6282','6715','8171']
def get(ds, c):
    url = f'https://api.finmindtrade.com/api/v4/data?dataset={ds}&data_id={c}&start_date=2020-01-01&end_date=2026-12-31'
    for i in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r:
                return json.load(r)
        except Exception as e:
            print('ERR', ds, c, e); time.sleep(4)
    return {}
out = {}
for c in codes:
    d = get('TaiwanStockDividend', c); rows = d.get('data') or []
    cr = get('TaiwanStockCapitalReductionReferencePrice', c).get('data') or []
    out[c] = {'div': [{k: x.get(k) for k in ('year','CashEarningsDistribution','CashStatutorySurplus','StockEarningsDistribution','StockStatutorySurplus','CashExDividendTradingDate','StockExDividendTradingDate','CashDividendPaymentDate','date','CashIncreaseSubscriptionRate','CashIncreaseSubscriptionpRrice')} for x in rows], 'cr': cr}
    print(c, d.get('msg'), len(rows), len(cr))
    time.sleep(1.5)
print('JSON>>>' + json.dumps(out, ensure_ascii=False) + '<<<JSON')
