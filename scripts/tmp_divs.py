import json, sys, os
sys.path.insert(0, os.path.dirname(__file__))
import fetch_market as fm
codes = ['2409','3056','3231','2324','00891','1434','2535','9945','2812','00940','00948B','0050','2317','00981A','00403A','00400A','2308','2383']
out = {}
for c in codes:
    got = None
    for otc in (False, True):
        try:
            got = fm.yahoo_dividends(c, otc)
            if got: break
        except Exception as e:
            print('ERR', c, otc, e)
    if not got and c.startswith('00'):
        try: got = fm.moneydj_dividends(c)
        except Exception as e: print('ERR mdj', c, e)
    out[c] = sorted(got or [], key=lambda e: e['ex'])
    print(c, len(out[c]), out[c][:1], out[c][-1:])
print('JSON>>>' + json.dumps(out, ensure_ascii=False) + '<<<JSON')
