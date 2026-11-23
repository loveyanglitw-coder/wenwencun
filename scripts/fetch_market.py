#!/usr/bin/env python3
"""每天抓全台股（上市＋上櫃，含 ETF）的收盤價與近期除權息，輸出 data/market.json 給 App 讀取。

資料來源（都是官方公開資料，只用 Python 標準函式庫）：
- 上市收盤價：證交所「每日收盤行情」MI_INDEX；抓不到再用證交所 OpenAPI STOCK_DAY_ALL。
- 上櫃收盤價：櫃買中心「上櫃股票行情」dailyQ；抓不到再用櫃買 OpenAPI。
- 除權息：證交所 OpenAPI「除權除息預告表」TWT48U_ALL、櫃買 OpenAPI 除權息預告。官方預告沒有發放日，
  舊資料裡已有的發放日會保留。

規則：
- 只有拿到「比舊資料新」的交易日收盤價才更新股價；拿到的還是舊的一天就保留原本股價。
- 除權息保留除息日在 60 天前到未來的每一筆，新的預告與舊資料合併。
"""
import datetime, html, json, os, re, sys, time, urllib.request

TW = datetime.timezone(datetime.timedelta(hours=8))
NOW = datetime.datetime.now(TW)
TODAY = NOW.date()
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
OUT = os.path.join(ROOT, 'data', 'market.json')
UA = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36',
      'Accept': 'application/json, text/plain, */*'}
# 只收股票與 ETF：4 碼個股、00 開頭的 ETF（含 00400A、00679B 這類），排除 6 碼的權證等
CODE_RE = re.compile(r'^(?:\d{4}[A-Z]?|00\d{2,4}[A-Z]?)$')
log = []


def say(msg):
    print(msg, flush=True)
    log.append(msg)


def get_json(url, tries=3):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode('utf-8-sig'))
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(3 * (i + 1))
    raise last


def num(v):
    """'1,234.50' → 1234.5；'--'、'' 或無法解析 → None"""
    if v is None:
        return None
    s = html.unescape(re.sub(r'<[^>]*>', '', str(v))).replace(',', '').replace('＋', '+').replace('－', '-').strip()
    if s in ('', '--', '---', '-', 'X', '除權', '除息', '除權息'):
        return None
    try:
        return float(s)
    except ValueError:
        m = re.search(r'[-+]?\d+(?:\.\d+)?', s)
        return float(m.group()) if m else None


def roc_to_iso(s):
    """民國日期 1151123 / 115/11/23 / 115-11-23 / 西元 2026/11/23 → 2026-11-23"""
    s = str(s or '').strip()
    m = re.match(r'^(\d{2,4})[/\-.年]?(\d{1,2})[/\-.月]?(\d{1,2})日?$', s) if not s.isdigit() else None
    if s.isdigit():
        if len(s) == 8:
            y, mo, d = int(s[:4]), int(s[4:6]), int(s[6:])
        elif len(s) in (6, 7):
            y, mo, d = int(s[:-4]), int(s[-4:-2]), int(s[-2:])
        else:
            return None
    elif m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        return None
    if y < 1911:
        y += 1911
    try:
        return datetime.date(y, mo, d).isoformat()
    except ValueError:
        return None


def pick(row, *keys):
    for k in keys:
        if k in row and row[k] not in (None, ''):
            return row[k]
    return None


def clean_name(n):
    return re.sub(r'\*+$', '', str(n or '').strip())


# ---------------- 收盤價 ----------------

def twse_mi_index(day):
    url = f'https://www.twse.com.tw/rwd/zh/afterTrading/MI_INDEX?date={day:%Y%m%d}&type=ALLBUT0999&response=json'
    j = get_json(url)
    if j.get('stat') != 'OK':
        raise RuntimeError(f"stat={j.get('stat')}")
    tables = j.get('tables') or []
    if not tables and j.get('fields9'):
        tables = [{'fields': j['fields9'], 'data': j.get('data9') or []}]
    out = {}
    for t in tables:
        f = t.get('fields') or []
        if '證券代號' not in f or '收盤價' not in f:
            continue
        ic, inm, icl = f.index('證券代號'), f.index('證券名稱'), f.index('收盤價')
        isg = f.index('漲跌(+/-)') if '漲跌(+/-)' in f else None
        idf = f.index('漲跌價差') if '漲跌價差' in f else None
        for r in t.get('data') or []:
            code = str(r[ic]).strip().upper()
            close = num(r[icl])
            if not CODE_RE.match(code) or close is None:
                continue
            chg = num(r[idf]) if idf is not None else 0.0
            sign = re.sub(r'<[^>]*>', '', str(r[isg])) if isg is not None else ''
            if chg is not None and '-' in sign:
                chg = -abs(chg)
            out[code] = {'price': close, 'chg': round(chg or 0.0, 4), 'name': clean_name(r[inm])}
    if not out:
        raise RuntimeError('MI_INDEX 沒有個股資料')
    return day.isoformat(), out


def twse_openapi():
    j = get_json('https://openapi.twse.com.tw/v1/exchangeReport/STOCK_DAY_ALL')
    out, dates = {}, set()
    for r in j:
        code = str(r.get('Code', '')).strip().upper()
        close = num(r.get('ClosingPrice'))
        if not CODE_RE.match(code) or close is None:
            continue
        d = roc_to_iso(r.get('Date'))
        if d:
            dates.add(d)
        out[code] = {'price': close, 'chg': round(num(r.get('Change')) or 0.0, 4), 'name': clean_name(r.get('Name'))}
    if not out:
        raise RuntimeError('STOCK_DAY_ALL 沒有資料')
    return (max(dates) if dates else None), out


def tpex_daily(day):
    url = f'https://www.tpex.org.tw/www/zh-tw/afterTrading/dailyQ?date={day:%Y/%m/%d}&response=json'
    j = get_json(url)
    tables = j.get('tables') or []
    out = {}
    for t in tables:
        f = t.get('fields') or []
        if '代號' not in f or '收盤' not in f:
            continue
        ic, inm, icl = f.index('代號'), f.index('名稱'), f.index('收盤')
        idf = f.index('漲跌') if '漲跌' in f else None
        for r in t.get('data') or []:
            code = str(r[ic]).strip().upper()
            close = num(r[icl])
            if not CODE_RE.match(code) or close is None:
                continue
            out[code] = {'price': close, 'chg': round(num(r[idf]) or 0.0, 4) if idf is not None else 0.0, 'name': clean_name(r[inm])}
    if not out:
        raise RuntimeError(f"dailyQ 沒有資料（stat={j.get('stat')}）")
    d = roc_to_iso(j.get('date')) or day.isoformat()
    return d, out


def tpex_openapi():
    j = get_json('https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes')
    out, dates = {}, set()
    for r in j:
        code = str(pick(r, 'SecuritiesCompanyCode', 'Code') or '').strip().upper()
        close = num(pick(r, 'Close', 'ClosingPrice'))
        if not CODE_RE.match(code) or close is None:
            continue
        d = roc_to_iso(r.get('Date'))
        if d:
            dates.add(d)
        out[code] = {'price': close, 'chg': round(num(r.get('Change')) or 0.0, 4), 'name': clean_name(pick(r, 'CompanyName', 'Name'))}
    if not out:
        raise RuntimeError('tpex openapi 沒有資料')
    return (max(dates) if dates else None), out


def fetch_market(label, primary, fallback):
    best = (None, {})
    for name, fn in (('主要', primary), ('備援', fallback)):
        try:
            d, data = fn()
            say(f'{label}{name}來源：{d}，{len(data)} 檔')
            if d and (best[0] is None or d > best[0]):
                best = (d, data)
            if d == TODAY.isoformat():
                break
        except Exception as e:  # noqa: BLE001
            say(f'{label}{name}來源失敗：{e}')
    return best


# ---------------- 除權息 ----------------

def twse_events():
    j = get_json('https://openapi.twse.com.tw/v1/exchangeReport/TWT48U_ALL')
    out = []
    for r in j:
        code = str(r.get('Code', '')).strip().upper()
        ex = roc_to_iso(r.get('Date'))
        if not CODE_RE.match(code) or not ex:
            continue
        cash = num(r.get('CashDividend'))
        ratio = num(r.get('StockDividendRatio'))  # 每股配股比率（股）
        out.append((code, ex, cash, ratio))
    return out


def tpex_events():
    j = get_json('https://www.tpex.org.tw/openapi/v1/tpex_exright_prepost')
    out = []
    for r in j:
        code = str(pick(r, 'SecuritiesCompanyCode', 'Code', 'StockCode') or '').strip().upper()
        ex = roc_to_iso(pick(r, 'ExRightsExDividendDate', 'ExDividendDate', 'ExRightDate', 'Date'))
        if not CODE_RE.match(code) or not ex:
            continue
        cash = num(pick(r, 'CashDividend', 'CashDividendPerShare'))
        ratio = num(pick(r, 'StockDividendRatio', 'StockDividend'))
        out.append((code, ex, cash, ratio))
    return out


def merge_events(old, rows):
    keep_from = (TODAY - datetime.timedelta(days=60)).isoformat()
    ev = {}
    for code, lst in (old or {}).items():
        for e in lst or []:
            if e.get('ex', '') >= keep_from:
                ev.setdefault(code, {})[e['ex']] = dict(e)
    added = 0
    for code, ex, cash, ratio in rows:
        if ex < keep_from:
            continue
        e = ev.setdefault(code, {}).get(ex)
        # App 的股票股利以「每股幾元」表示（配股率 × 10）
        stock = round(ratio * 10, 6) if ratio else 0
        if e is None:
            if cash is None and not stock:
                continue  # 金額還沒公布
            ev[code][ex] = {'ex': ex, 'cash': cash or 0, 'stock': stock}
            added += 1
        else:
            if cash is not None:
                e['cash'] = cash
            if stock:
                e['stock'] = stock
    return {c: sorted(d.values(), key=lambda x: x['ex']) for c, d in ev.items() if d}, added


def main():
    try:
        with open(OUT, encoding='utf-8') as f:
            old = json.load(f)
    except Exception:  # noqa: BLE001
        old = {}
    days = [TODAY - datetime.timedelta(days=i) for i in range(0, 5)]

    def twse_primary():
        for d in days:
            if d.weekday() < 5:
                try:
                    return twse_mi_index(d)
                except Exception as e:  # noqa: BLE001
                    say(f'  MI_INDEX {d}：{e}')
        raise RuntimeError('近 5 天都沒有資料')

    def tpex_primary():
        for d in days:
            if d.weekday() < 5:
                try:
                    return tpex_daily(d)
                except Exception as e:  # noqa: BLE001
                    say(f'  dailyQ {d}：{e}')
        raise RuntimeError('近 5 天都沒有資料')

    d1, p1 = fetch_market('上市', twse_primary, twse_openapi)
    d2, p2 = fetch_market('上櫃', tpex_primary, tpex_openapi)

    old_date = old.get('date') or ''
    prices = dict(old.get('prices') or {})
    new_date = old_date
    for d, p in ((d1, p1), (d2, p2)):
        if d and p and d >= old_date:
            prices.update(p)
            new_date = max(new_date, d)
    price_changed = new_date != old_date

    rows = []
    for label, fn in (('上市', twse_events), ('上櫃', tpex_events)):
        try:
            r = fn()
            say(f'{label}除權息預告：{len(r)} 筆')
            rows += r
        except Exception as e:  # noqa: BLE001
            say(f'{label}除權息預告失敗：{e}')
    events, added = merge_events(old.get('events'), rows)
    say(f'除權息合計 {sum(len(v) for v in events.values())} 筆（新增 {added}）')

    if not prices:
        say('沒有任何股價資料，不寫入')
        sys.exit(1)
    data = {
        'date': new_date,
        'updated': NOW.strftime('%Y-%m-%d %H:%M'),
        'source': '臺灣證券交易所、櫃買中心',
        'sources': {'股價': f'上市 {d1 or "無"}、上櫃 {d2 or "無"}，共 {len(prices)} 檔', '除權息': '證交所、櫃買中心除權除息預告表'},
        'prices': dict(sorted(prices.items())),
        'events': dict(sorted(events.items())),
    }
    if not price_changed and data['events'] == (old.get('events') or {}):
        say(f'股價仍是 {old_date}，除權息也沒有變動，不更新')
        return
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))
    say(f'已寫入：股價日期 {new_date}，{len(prices)} 檔')


if __name__ == '__main__':
    main()
