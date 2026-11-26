import json, urllib.request, time
codes = ['2409','3056','3231','2324','00891','1434','2535','9945','2812','00940','00948B','0050','2317','00981A','00403A','00400A','2308','2383']
for c in codes:
    url = f'https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockCapitalReductionReferencePrice&data_id={c}&start_date=2021-01-01&end_date=2026-12-31'
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=30) as r: d = json.load(r)
    except Exception as e:
        print('ERR', c, e); d = {}
    print('CR', c, d.get('msg'), json.dumps(d.get('data') or [], ensure_ascii=False))
    time.sleep(1)
