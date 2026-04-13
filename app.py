# ============================================================
# 🔍 主力進場訊號掃描器 v9（修正 TPEX 被擋問題）
# ============================================================

import streamlit as st
import pandas as pd
import requests
import time
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

# TPEX 需要完整 headers 才不會被擋
HEADERS_TWSE = {"User-Agent": "Mozilla/5.0"}
HEADERS_TPEX = {
    "User-Agent"      : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Referer"         : "https://www.tpex.org.tw/",
    "Accept"          : "application/json, text/javascript, */*; q=0.01",
    "Accept-Language" : "zh-TW,zh;q=0.9",
    "X-Requested-With": "XMLHttpRequest",
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
v2_max       = st.sidebar.slider("訊號三：量比上限",              3.0, 8.0, 4.0, 0.5)
market_opt   = st.sidebar.multiselect("市場", ["上市", "上櫃"], default=["上市", "上櫃"])

if st.sidebar.button("🗑️ 清除快取重新抓資料"):
    st.cache_data.clear()
    st.sidebar.success("快取已清除！")

# ════════════════════════════════════════════════════════════
# 工具函數
# ════════════════════════════════════════════════════════════

def clean_num(series):
    return pd.to_numeric(
        series.astype(str).str.replace(",", "").str.replace(" ", "").str.strip(),
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
# TPEX 抓取（session + 完整 headers）
# ════════════════════════════════════════════════════════════

def fetch_tpex_day(session, d, log):
    dt  = datetime.strptime(d, "%Y%m%d")
    roc = f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"

    # 先訪問首頁取得 cookies
    try:
        session.get("https://www.tpex.org.tw/", timeout=10, verify=False)
    except:
        pass

    url = (
        "https://www.tpex.org.tw/web/stock/aftertrading/"
        f"all_daily_info/mpsas_result.php?l=zh-tw&o=json&d={roc}&s=0,asc"
    )
    resp = session.get(url, timeout=15, verify=False)
    raw  = resp.text.strip()

    if not raw or raw[0] not in "[{":
        # 嘗試備用 URL 格式
        url2 = (
            "https://www.tpex.org.tw/web/stock/aftertrading/"
            f"all_daily_info/mpsas_result.php?l=zh-tw&o=json&d={roc}"
        )
        resp = session.get(url2, timeout=15, verify=False)
        raw  = resp.text.strip()

    if not raw or raw[0] not in "[{":
        log.append(f"  TPEX {d}：空白回應（{len(raw)} chars）")
        return None

    data = resp.json()
    rows = data.get("aaData") or data.get("data") or []
    log.append(f"  TPEX {d}：{len(rows)} 筆")
    return rows

# ════════════════════════════════════════════════════════════
# TPEX OpenAPI（備援方案）
# ════════════════════════════════════════════════════════════

def fetch_tpex_openapi(d, log):
    dt  = datetime.strptime(d, "%Y%m%d")
    roc = f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"
    url = f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes?date={roc}"
    resp = requests.get(url, timeout=15, headers=HEADERS_TPEX, verify=False)
    raw  = resp.text.strip()
    if not raw or raw[0] not in "[{":
        log.append(f"  TPEX OpenAPI {d}：空白（{len(raw)} chars）")
        return None
    data = resp.json()
    log.append(f"  TPEX OpenAPI {d}：{len(data)} 筆")
    return data

# ════════════════════════════════════════════════════════════
# 主要資料抓取
# ════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def fetch_all_data():
    NEED     = 8
    weekdays = get_weekdays()
    log      = []
    warnings_out = []

    # ── 上市發行股數 ──────────────────────────────────────
    r = requests.get(
        "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
        timeout=15, headers=HEADERS_TWSE, verify=False
    )
    raw = pd.DataFrame(r.json())
    col = [c for c in raw.columns if "發行" in c and "股" in c][0]
    twse_shares = raw[["公司代號", col]].copy()
    twse_shares.columns = ["stock_id", "shares"]
    twse_shares["stock_id"] = twse_shares["stock_id"].str.strip()
    twse_shares["shares"] = clean_num(twse_shares["shares"])
    twse_shares = twse_shares.dropna().query("shares > 0").reset_index(drop=True)
    log.append(f"【TWSE】發行股數：{len(twse_shares)} 檔")

    # ── 上市每日資料 ──────────────────────────────────────
    twse_frames = []
    for d in weekdays:
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json&date={d}"
        try:
            resp = requests.get(url, timeout=15, headers=HEADERS_TWSE, verify=False)
            data = resp.json()
            if data.get("stat") == "OK" and len(data.get("data", [])) > 50:
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = pd.to_datetime(d, format="%Y%m%d")
                twse_frames.append(df)
                log.append(f"  TWSE {d}：{len(df)} 筆 ✅")
        except Exception as e:
            log.append(f"  TWSE {d}：{e}")
        if len(twse_frames) >= NEED:
            break
        time.sleep(0.4)

    if not twse_frames:
        raise ValueError("TWSE_EMPTY|" + "\n".join(log))

    twse_raw = pd.concat(twse_frames, ignore_index=True)
    twse_raw = twse_raw.rename(columns={
        "證券代號": "stock_id", "證券名稱": "stock_name",
        "成交股數": "vol_str", "開盤價": "open_str", "收盤價": "close_str"
    })
    twse_raw["stock_id"] = twse_raw["stock_id"].str.strip()
    twse_raw["volume"]   = clean_num(twse_raw["vol_str"])
    twse_raw["open"]     = clean_num(twse_raw["open_str"])
    twse_raw["close"]    = clean_num(twse_raw["close_str"])
    twse_raw["market"]   = "上市"
    twse = twse_raw.merge(twse_shares, on="stock_id", how="inner")
    twse = twse.dropna(subset=["volume","shares","open","close"])
    twse = twse.query("volume>0 and shares>0 and close>0").copy()
    twse["turnover_rate"] = (twse["volume"] / twse["shares"]) * 100
    log.append(f"【TWSE】整合完成：{twse['stock_id'].nunique()} 檔 ✅")

    # ── 上櫃每日資料（session 方式）──────────────────────
    log.append("【TPEX】嘗試 Session 方式...")
    TPEX_COLS = [
        "stock_id","stock_name","close_str","change",
        "open_str","high","low","vol_str","amount","trades",
        "bid_p","bid_v","ask_p","ask_v","shares_str","limit_up","limit_down"
    ]

    tpex_session = requests.Session()
    tpex_session.headers.update(HEADERS_TPEX)
    tpex_frames  = []

    for d in weekdays:
        try:
            rows = fetch_tpex_day(tpex_session, d, log)
            if rows and len(rows) > 50:
                n  = len(rows[0])
                df = pd.DataFrame(rows, columns=TPEX_COLS[:n])
                df["date"] = pd.to_datetime(d, format="%Y%m%d")
                tpex_frames.append(df)
        except Exception as e:
            log.append(f"  TPEX {d}：{e}")
        if len(tpex_frames) >= NEED:
            break
        time.sleep(0.5)

    # ── 備援：TPEX OpenAPI ────────────────────────────────
    if not tpex_frames:
        log.append("【TPEX】Session 失敗，改用 OpenAPI...")
        openapi_frames = []
        for d in weekdays:
            try:
                data = fetch_tpex_openapi(d, log)
                if data and len(data) > 50:
                    df = pd.DataFrame(data)
                    df["date"] = pd.to_datetime(d, format="%Y%m%d")
                    openapi_frames.append(df)
                    if len(openapi_frames) == 1:
                        log.append(f"  欄位：{list(df.columns)}")
            except Exception as e:
                log.append(f"  OpenAPI {d}：{e}")
            if len(openapi_frames) >= NEED:
                break
            time.sleep(0.5)

        if openapi_frames:
            tpex_api = pd.concat(openapi_frames, ignore_index=True)
            # 自動對應欄位
            rename = {}
            for c in tpex_api.columns:
                cl = c.lower()
                if "code" in cl or "id" in cl:     rename[c] = "stock_id"
                elif "name" in cl:                  rename[c] = "stock_name"
                elif "close" in cl:                 rename[c] = "close_str"
                elif "open" in cl:                  rename[c] = "open_str"
                elif "volume" in cl or "qty" in cl: rename[c] = "vol_str"
                elif "issue" in cl or "share" in cl:rename[c] = "shares_str"
            tpex_api = tpex_api.rename(columns=rename)
            tpex_api["stock_id"] = tpex_api["stock_id"].astype(str).str.strip()
            tpex_api["volume"]   = clean_num(tpex_api.get("vol_str",    pd.Series(dtype=str)))
            tpex_api["shares"]   = clean_num(tpex_api.get("shares_str", pd.Series(dtype=str)))
            tpex_api["open"]     = clean_num(tpex_api.get("open_str",   pd.Series(dtype=str)))
            tpex_api["close"]    = clean_num(tpex_api.get("close_str",  pd.Series(dtype=str)))
            tpex_api["market"]   = "上櫃"
            tpex_api = tpex_api.dropna(subset=["volume","shares","open","close"])
            tpex_api = tpex_api.query("volume>0 and shares>0 and close>0").copy()
            tpex_api["turnover_rate"] = (tpex_api["volume"] / tpex_api["shares"]) * 100
            tpex_final = tpex_api
            log.append(f"【TPEX】OpenAPI 整合：{tpex_api['stock_id'].nunique()} 檔 ✅")
        else:
            warnings_out.append("上櫃（TPEX）資料暫時無法取得，本次只掃描上市股票")
            log.append("【TPEX】兩種方式均失敗，跳過上櫃")
            KEEP = ["stock_id","stock_name","date","open","close",
                    "volume","shares","turnover_rate","market"]
            df = twse[KEEP].copy().sort_values(["stock_id","date"]).reset_index(drop=True)
            return df, log, warnings_out
    else:
        tpex_raw = pd.concat(tpex_frames, ignore_index=True)
        tpex_raw["stock_id"] = tpex_raw["stock_id"].str.strip()
        tpex_raw["volume"]   = clean_num(tpex_raw["vol_str"])
        tpex_raw["shares"]   = clean_num(tpex_raw["shares_str"])
        tpex_raw["open"]     = clean_num(tpex_raw["open_str"])
        tpex_raw["close"]    = clean_num(tpex_raw["close_str"])
        tpex_raw["market"]   = "上櫃"
        tpex_final = tpex_raw.dropna(subset=["volume","shares","open","close"])
        tpex_final = tpex_final.query("volume>0 and shares>0 and close>0").copy()
        tpex_final["turnover_rate"] = (tpex_final["volume"] / tpex_final["shares"]) * 100
        log.append(f"【TPEX】Session 整合：{tpex_final['stock_id'].nunique()} 檔 ✅")

    KEEP = ["stock_id","stock_name","date","open","close",
            "volume","shares","turnover_rate","market"]
    df = pd.concat([twse[KEEP], tpex_final[KEEP]], ignore_index=True)
    df = df.sort_values(["stock_id","date"]).reset_index(drop=True)
    return df, log, warnings_out

# ════════════════════════════════════════════════════════════
# 三訊號掃描
# ════════════════════════════════════════════════════════════

def run_scan(df, t1, t2_min, t2_mult, v_min, v_max, markets):
    latest  = df["date"].max()
    df      = df[df["market"].isin(markets)]
    results = []
    for sid, group in df.groupby("stock_id"):
        group    = group.sort_values("date")
        today_r  = group[group["date"] == latest]
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
        s1 = t_avg5  < t1
        s2 = t_today >= t2_min and t_ratio >= t2_mult
        s3 = v_min <= v_ratio <= v_max
        if s1 and s2 and s3:
            chg = round(((row["close"]-row["open"])/row["open"])*100, 2) \
                  if row["open"] > 0 else 0
            results.append({
                "市場"         : row["market"],
                "代號"         : sid,
                "名稱"         : row.get("stock_name", sid),
                "收盤價"       : row["close"],
                "當日漲跌(%)"  : chg,
                "五日均週轉(%)": round(t_avg5,  3),
                "今日週轉(%)"  : round(t_today, 3),
                "週轉率倍數"   : round(t_ratio,  1),
                "量比"         : round(v_ratio,  1),
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
    st.warning(f"⚠️ 今天是星期{weekday_zh[today.weekday()]}（非交易日），將以最近交易日為基準。")

if st.button("🚀 開始掃描", type="primary", use_container_width=True):
    with st.spinner("📡 抓取 TWSE / TPEX 資料中，約需 60～90 秒..."):
        try:
            df, log, warnings_list = fetch_all_data()
            latest_available = df["date"].max().strftime("%Y-%m-%d")
            markets_in_df    = df["market"].unique().tolist()
            st.success(
                f"✅ 資料載入完成：{df['stock_id'].nunique()} 檔 × "
                f"{df['date'].nunique()} 天（最新：{latest_available}）｜"
                f"市場：{' / '.join(markets_in_df)}"
            )
            for w in warnings_list:
                st.warning(f"⚠️ {w}")
            with st.expander("🔍 資料抓取 log"):
                st.text("\n".join(log))
        except ValueError as e:
            msg    = str(e)
            detail = msg.split("|")[1] if "|" in msg else ""
            st.error(f"❌ {msg.split('|')[0]}")
            if detail:
                with st.expander("🔍 詳細 log"):
                    st.text(detail)
            st.info("💡 請點左側「🗑️ 清除快取」後再試")
            st.stop()
        except Exception as e:
            st.error(f"❌ {e}")
            st.stop()

    with st.spinner("🔍 執行三訊號掃描..."):
        result_df, latest_date = run_scan(
            df, t1_threshold, t2_min, t2_mult, v2_min, v2_max, market_opt
        )

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
            color = "red" if val > 0 else ("green" if val < 0 else "gray")
            return f"color: {color}"
        styled = result_df.style.applymap(color_chg, subset=["當日漲跌(%)"])
        st.dataframe(styled, use_container_width=True, height=500)
        csv = result_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button("💾 下載 CSV", csv,
            f"主力訊號_{latest_date.strftime('%Y%m%d')}.csv", "text/csv",
            use_container_width=True)
    else:
        st.info("此交易日無符合三條件的股票，可調整左側參數後重新掃描")
else:
    st.info("👈 調整左側參數後，按「開始掃描」")
