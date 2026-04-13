# ============================================================
# 🔍 主力進場訊號掃描器 v11（改用 MIS TPEX API）
# ============================================================

import streamlit as st
import pandas as pd
import requests
import time
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

HEADERS = {
    "User-Agent"      : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept"          : "application/json, text/javascript, */*; q=0.01",
    "Accept-Language" : "zh-TW,zh;q=0.9",
}

st.set_page_config(page_title="主力進場訊號掃描器", page_icon="🔍", layout="wide")
st.title("🔍 主力進場訊號掃描器")
st.caption("涵蓋上市＋上櫃全部股票 ｜ 資料來源：TWSE / TPEX 官方 API")

with st.expander("📋 三訊號說明（點此展開）"):
    c1, c2, c3 = st.columns(3)
    c1.info("**訊號一**\n\n五日均週轉率 < 1%\n\n沉寂冷門股，沒人在玩")
    c2.info("**訊號二**\n\n今日週轉率 ≥ 2.5%\n且為五日均值的 3 倍以上\n\n主力突然進場")
    c3.info("**訊號三**\n\n今日成交量為五日均量的 2～4 倍\n（超過 5 倍可能是出貨）\n\n量能健康放大")

st.sidebar.header("⚙️ 掃描參數")
t1_threshold = st.sidebar.slider("訊號一：五日均週轉率上限 (%)", 0.5, 2.0, 1.0, 0.1)
t2_min       = st.sidebar.slider("訊號二：今日週轉率下限 (%)",   1.5, 5.0, 2.5, 0.1)
t2_mult      = st.sidebar.slider("訊號二：週轉率倍數下限",        2.0, 5.0, 3.0, 0.5)
v2_min       = st.sidebar.slider("訊號三：量比下限",              1.0, 3.0, 2.0, 0.5)
v2_max       = st.sidebar.slider("訊號三：量比上限",              3.0, 8.0, 5.0, 0.5)
market_opt   = st.sidebar.multiselect("市場", ["上市", "上櫃"], default=["上市", "上櫃"])

if st.sidebar.button("🗑️ 清除快取重新抓資料"):
    st.cache_data.clear()
    st.sidebar.success("快取已清除！")

# ════════════════════════════════════════════════════════════
# 工具函數
# ════════════════════════════════════════════════════════════

def clean_num(s):
    if isinstance(s, pd.DataFrame):
        s = s.iloc[:, 0]
    return pd.to_numeric(
        pd.Series(s).astype(str).str.replace(",", "").str.replace(" ", "").str.strip(),
        errors="coerce"
    )

def get_weekdays(n=30):
    dates, d = [], datetime.today()
    for _ in range(n):
        if d.weekday() < 5:
            dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates

# ════════════════════════════════════════════════════════════
# TWSE 每日資料
# ════════════════════════════════════════════════════════════

def fetch_twse_shares():
    r = requests.get(
        "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
        timeout=15, headers=HEADERS, verify=False
    )
    raw = pd.DataFrame(r.json())
    col = [c for c in raw.columns if "發行" in c and "股" in c][0]
    df  = raw[["公司代號", col]].copy()
    df.columns = ["stock_id", "shares"]
    df["stock_id"] = df["stock_id"].str.strip()
    df["shares"]   = clean_num(df["shares"])
    return df.dropna().query("shares > 0").reset_index(drop=True)

def fetch_twse_day(d, log):
    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json&date={d}"
    try:
        resp = requests.get(url, timeout=15, headers=HEADERS, verify=False)
        data = resp.json()
        if data.get("stat") == "OK" and len(data.get("data", [])) > 50:
            df = pd.DataFrame(data["data"], columns=data["fields"])
            df["date"] = pd.to_datetime(d, format="%Y%m%d")
            log.append(f"  TWSE {d}：{len(df)} 筆 ✅")
            return df
    except Exception as e:
        log.append(f"  TWSE {d}：{e}")
    return None

# ════════════════════════════════════════════════════════════
# TPEX 每日資料 — 三種 API 依序嘗試
# ════════════════════════════════════════════════════════════

TPEX_COLS = [
    "stock_id","stock_name","close_str","change",
    "open_str","high","low","vol_str","amount","trades",
    "bid_p","bid_v","ask_p","ask_v","shares_str","limit_up","limit_down"
]

def _tpex_rows_to_df(rows, d):
    """舊式 aaData list-of-list 轉 DataFrame"""
    n  = len(rows[0])
    df = pd.DataFrame(rows, columns=TPEX_COLS[:n])
    df["date"] = pd.to_datetime(d, format="%Y%m%d")
    return df

def fetch_tpex_day(d, log):
    dt  = datetime.strptime(d, "%Y%m%d")
    roc = f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"

    # ── 方法 1：TPEX 主站（加 session + cookies）──────────
    try:
        sess = requests.Session()
        sess.headers.update({**HEADERS, "Referer": "https://www.tpex.org.tw/"})
        sess.get("https://www.tpex.org.tw/", timeout=8, verify=False)
        url  = (
            "https://www.tpex.org.tw/web/stock/aftertrading/"
            f"all_daily_info/mpsas_result.php?l=zh-tw&o=json&d={roc}&s=0,asc"
        )
        resp = sess.get(url, timeout=12, verify=False)
        raw  = resp.text.strip()
        if raw and raw[0] in "[{":
            rows = resp.json().get("aaData") or []
            if len(rows) > 50:
                log.append(f"  TPEX主站 {d}：{len(rows)} 筆 ✅")
                return _tpex_rows_to_df(rows, d)
    except Exception as e:
        log.append(f"  TPEX主站 {d}：{e}")

    # ── 方法 2：TPEX OpenAPI（openapi.tpex.org.tw）────────
    for api_url in [
        f"https://openapi.tpex.org.tw/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8",
        f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8",
    ]:
        try:
            resp = requests.get(api_url, timeout=12, headers=HEADERS, verify=False)
            raw  = resp.text.strip()
            if raw and raw[0] in "[{":
                data = resp.json()
                if isinstance(data, list) and len(data) > 50:
                    log.append(f"  TPEX OpenAPI {d}：{len(data)} 筆，欄位={list(data[0].keys())[:5]} ✅")
                    df = pd.DataFrame(data)
                    df["date"] = pd.to_datetime(d, format="%Y%m%d")
                    return df
        except Exception as e:
            log.append(f"  TPEX OpenAPI {d}：{e}")

    # ── 方法 3：TPEX MIS API ──────────────────────────────
    try:
        url  = f"https://mis.tpex.org.tw/api/getPTSStockSummaryByDate?d={roc}&o=json"
        resp = requests.get(url, timeout=12, headers=HEADERS, verify=False)
        raw  = resp.text.strip()
        if raw and raw[0] in "[{":
            data = resp.json()
            rows = data.get("aaData") or (data if isinstance(data, list) else [])
            if len(rows) > 50:
                log.append(f"  TPEX MIS {d}：{len(rows)} 筆 ✅")
                return _tpex_rows_to_df(rows, d) if isinstance(rows[0], list) else pd.DataFrame(rows)
    except Exception as e:
        log.append(f"  TPEX MIS {d}：{e}")

    log.append(f"  TPEX {d}：三種方式均失敗")
    return None

def process_tpex_df(df, log):
    """統一處理 TPEX DataFrame（無論來源）"""
    df = df.copy()
    df = df.loc[:, ~df.columns.duplicated()]
    cols = list(df.columns)

    # 若是舊式 TPEX_COLS 格式
    if "vol_str" in cols and "shares_str" in cols:
        df["stock_id"] = df["stock_id"].astype(str).str.strip()
        df["volume"]   = clean_num(df["vol_str"])
        df["shares"]   = clean_num(df["shares_str"])
        df["open"]     = clean_num(df["open_str"])
        df["close"]    = clean_num(df["close_str"])
        df["market"]   = "上櫃"
        return df.dropna(subset=["volume","shares","open","close"]).query(
            "volume>0 and shares>0 and close>0"
        ).assign(turnover_rate=lambda x: x["volume"]/x["shares"]*100)

    # OpenAPI 格式 — 自動對應
    FIELD_MAP = {
        "SecuritiesCompanyCode": "stock_id",  "Code": "stock_id",
        "CompanyName": "stock_name",           "Name": "stock_name",
        "Close": "close",    "ClosingPrice": "close",
        "Open":  "open",     "OpeningPrice": "open",
        "TradeVolume": "volume", "TradingShares": "volume",
        "IssuedShares": "shares","ListedShares": "shares",
    }
    df = df.rename(columns={k:v for k,v in FIELD_MAP.items() if k in cols})
    df = df.loc[:, ~df.columns.duplicated()]
    log.append(f"    OpenAPI 對應後欄位：{list(df.columns)[:8]}")

    for c in ["stock_id","close","open","volume","shares"]:
        if c not in df.columns:
            log.append(f"    ⚠️ 缺少欄位 {c}，跳過")
            return None

    df["stock_id"] = df["stock_id"].astype(str).str.strip()
    df["stock_name"] = df.get("stock_name", df["stock_id"])
    for c in ["volume","shares","open","close"]:
        df[c] = clean_num(df[c])
    df["market"] = "上櫃"
    df = df.dropna(subset=["volume","shares","open","close"])
    df = df.query("volume>0 and shares>0 and close>0").copy()
    df["turnover_rate"] = df["volume"] / df["shares"] * 100
    return df

# ════════════════════════════════════════════════════════════
# 主要資料抓取
# ════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def fetch_all_data():
    NEED     = 8
    weekdays = get_weekdays()
    log      = []
    warnings_out = []

    # 上市發行股數
    twse_shares = fetch_twse_shares()
    log.append(f"【TWSE 發行股數】{len(twse_shares)} 檔")

    # 上市每日資料
    twse_frames = []
    for d in weekdays:
        df = fetch_twse_day(d, log)
        if df is not None:
            twse_frames.append(df)
        if len(twse_frames) >= NEED:
            break
        time.sleep(0.4)

    if not twse_frames:
        raise ValueError("TWSE_EMPTY|" + "\n".join(log))

    twse_raw = pd.concat(twse_frames, ignore_index=True)
    twse_raw = twse_raw.rename(columns={
        "證券代號":"stock_id","證券名稱":"stock_name",
        "成交股數":"vol_str","開盤價":"open_str","收盤價":"close_str"
    })
    twse_raw["stock_id"] = twse_raw["stock_id"].str.strip()
    twse_raw["volume"]   = clean_num(twse_raw["vol_str"])
    twse_raw["open"]     = clean_num(twse_raw["open_str"])
    twse_raw["close"]    = clean_num(twse_raw["close_str"])
    twse_raw["market"]   = "上市"
    twse = twse_raw.merge(twse_shares, on="stock_id", how="inner")
    twse = twse.dropna(subset=["volume","shares","open","close"])
    twse = twse.query("volume>0 and shares>0 and close>0").copy()
    twse["turnover_rate"] = twse["volume"] / twse["shares"] * 100
    log.append(f"【TWSE 整合】{twse['stock_id'].nunique()} 檔 ✅")

    # 上櫃每日資料
    log.append("【TPEX】開始抓取...")
    tpex_dfs = []
    for d in weekdays:
        df = fetch_tpex_day(d, log)
        if df is not None:
            processed = process_tpex_df(df, log)
            if processed is not None and len(processed) > 50:
                tpex_dfs.append(processed)
        if len(tpex_dfs) >= NEED:
            break
        time.sleep(0.5)

    KEEP = ["stock_id","stock_name","date","open","close",
            "volume","shares","turnover_rate","market"]

    if tpex_dfs:
        tpex_all = pd.concat(tpex_dfs, ignore_index=True)
        log.append(f"【TPEX 整合】{tpex_all['stock_id'].nunique()} 檔 ✅")
        df_all = pd.concat([twse[KEEP], tpex_all[KEEP]], ignore_index=True)
    else:
        warnings_out.append("上櫃（TPEX）資料暫時無法取得，本次只掃描上市股票")
        log.append("【TPEX】全部失敗，跳過上櫃")
        df_all = twse[KEEP].copy()

    df_all = df_all.sort_values(["stock_id","date"]).reset_index(drop=True)
    return df_all, log, warnings_out

# ════════════════════════════════════════════════════════════
# 三訊號掃描
# ════════════════════════════════════════════════════════════

def run_scan(df, t1, t2_min, t2_mult, v_min, v_max, markets):
    latest  = df["date"].max()
    df      = df[df["market"].isin(markets)]
    results = []
    for sid, group in df.groupby("stock_id"):
        group   = group.sort_values("date")
        today_r = group[group["date"] == latest]
        if today_r.empty:
            continue
        past_5 = group[group["date"] < latest].tail(5)
        if len(past_5) < 5:
            continue
        row     = today_r.iloc[0]
        t_today = row["turnover_rate"]
        t_avg5  = past_5["turnover_rate"].mean()
        v_today = row["volume"]
        v_avg5  = past_5["volume"].mean()
        if t_avg5 <= 0 or v_avg5 <= 0:
            continue
        t_ratio = t_today / t_avg5
        v_ratio = v_today / v_avg5
        if t_avg5 < t1 and t_today >= t2_min and t_ratio >= t2_mult and v_min <= v_ratio <= v_max:
            chg = round(((row["close"]-row["open"])/row["open"])*100, 2) if row["open"] > 0 else 0
            results.append({
                "市場": row["market"], "代號": sid,
                "名稱": row.get("stock_name", sid),
                "收盤價": row["close"], "當日漲跌(%)": chg,
                "五日均週轉(%)": round(t_avg5, 3),
                "今日週轉(%)":   round(t_today, 3),
                "週轉率倍數":    round(t_ratio, 1),
                "量比":          round(v_ratio, 1),
            })
    rdf = pd.DataFrame(results)
    if len(rdf) > 0:
        rdf = rdf.sort_values("週轉率倍數", ascending=False).reset_index(drop=True)
    return rdf, latest

# ════════════════════════════════════════════════════════════
# 主畫面
# ════════════════════════════════════════════════════════════

today      = datetime.today()
weekday_zh = ["一","二","三","四","五","六","日"]
if today.weekday() >= 5:
    st.warning(f"⚠️ 今天是星期{weekday_zh[today.weekday()]}，將以最近交易日為基準。")

if st.button("🚀 開始掃描", type="primary", use_container_width=True):
    with st.spinner("📡 抓取資料中，約需 60～90 秒..."):
        try:
            df, log, warnings_list = fetch_all_data()
            latest_str    = df["date"].max().strftime("%Y-%m-%d")
            markets_in_df = df["market"].unique().tolist()
            st.success(f"✅ 資料載入完成：{df['stock_id'].nunique()} 檔 × {df['date'].nunique()} 天（最新：{latest_str}）｜市場：{' / '.join(markets_in_df)}")
            for w in warnings_list:
                st.warning(f"⚠️ {w}")
            with st.expander("🔍 資料抓取 log"):
                st.text("\n".join(log))
        except ValueError as e:
            msg = str(e); detail = msg.split("|")[1] if "|" in msg else ""
            st.error(f"❌ {msg.split('|')[0]}")
            if detail:
                with st.expander("🔍 詳細 log"): st.text(detail)
            st.info("💡 請點左側「🗑️ 清除快取」後再試"); st.stop()
        except Exception as e:
            import traceback
            st.error(f"❌ {e}")
            with st.expander("🔍 詳細錯誤"): st.text(traceback.format_exc())
            st.stop()

    with st.spinner("🔍 執行三訊號掃描..."):
        result_df, latest_date = run_scan(df, t1_threshold, t2_min, t2_mult, v2_min, v2_max, market_opt)

    st.markdown("---")
    st.subheader(f"🎯 掃描結果 — {latest_date.strftime('%Y-%m-%d')}")
    twse_n = len(result_df[result_df["市場"]=="上市"]) if len(result_df) > 0 else 0
    tpex_n = len(result_df[result_df["市場"]=="上櫃"]) if len(result_df) > 0 else 0
    c1, c2, c3 = st.columns(3)
    c1.metric("符合股票總數", f"{len(result_df)} 檔")
    c2.metric("上市", f"{twse_n} 檔")
    c3.metric("上櫃", f"{tpex_n} 檔")

    if len(result_df) > 0:
        def color_chg(val):
            return f"color: {'red' if val > 0 else 'green' if val < 0 else 'gray'}"
        st.dataframe(result_df.style.applymap(color_chg, subset=["當日漲跌(%)"]),
                     use_container_width=True, height=500)
        csv = result_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("💾 下載 CSV", csv,
            f"主力訊號_{latest_date.strftime('%Y%m%d')}.csv", "text/csv",
            use_container_width=True)
    else:
        # 顯示統計幫助用戶判斷條件是否合理
        st.info("此交易日無符合三條件的股票")
        st.markdown("#### 📊 今日市場參考數據")
        today_df = df[df["date"] == df["date"].max()]
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("掃描股票數", f"{len(today_df)} 檔")
        c2.metric("週轉率中位數", f"{today_df['turnover_rate'].median():.2f}%")
        c3.metric("週轉率最大值", f"{today_df['turnover_rate'].max():.2f}%")
        c4.metric("週轉率 > 2.5% 的股票", f"{(today_df['turnover_rate'] >= 2.5).sum()} 檔")
else:
    st.info("👈 調整左側參數後，按「開始掃描」")
