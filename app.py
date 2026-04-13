# ============================================================
# 🔍 主力進場訊號掃描器 v8（TPEX 雙 API 備援）
# ============================================================

import streamlit as st
import pandas as pd
import requests
import time
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

HEADERS = {"User-Agent": "Mozilla/5.0"}

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
# TPEX：嘗試兩種 API
# ════════════════════════════════════════════════════════════

def fetch_tpex_old(d, log):
    """舊版 TPEX API（民國年格式）"""
    dt  = datetime.strptime(d, "%Y%m%d")
    roc = f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"
    url = (
        "https://www.tpex.org.tw/web/stock/aftertrading/"
        f"all_daily_info/mpsas_result.php?l=zh-tw&o=json&d={roc}"
    )
    resp = requests.get(url, timeout=15, headers=HEADERS, verify=False)
    data = resp.json()
    rows = data.get("aaData") or data.get("data") or []
    log.append(f"    舊API {d}：HTTP {resp.status_code}，{len(rows)} 筆，keys={list(data.keys())[:5]}")
    return rows

def fetch_tpex_new(d, log):
    """新版 TPEX OpenAPI"""
    dt  = datetime.strptime(d, "%Y%m%d")
    roc = f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"
    url = f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8"
    resp = requests.get(url, timeout=15, headers=HEADERS, verify=False)
    data = resp.json()
    log.append(f"    新API {d}：HTTP {resp.status_code}，{len(data)} 筆")
    return data  # list of dicts

# ════════════════════════════════════════════════════════════
# 主要資料抓取
# ════════════════════════════════════════════════════════════

@st.cache_data(ttl=1800)
def fetch_all_data():
    NEED     = 8
    weekdays = get_weekdays()
    log      = []

    # ── 上市發行股數 ──────────────────────────────────────
    log.append("【TWSE 發行股數】")
    r = requests.get(
        "https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
        timeout=15, headers=HEADERS, verify=False
    )
    raw = pd.DataFrame(r.json())
    col = [c for c in raw.columns if "發行" in c and "股" in c][0]
    twse_shares = raw[["公司代號", col]].copy()
    twse_shares.columns = ["stock_id", "shares"]
    twse_shares["stock_id"] = twse_shares["stock_id"].str.strip()
    twse_shares["shares"] = clean_num(twse_shares["shares"])
    twse_shares = twse_shares.dropna().query("shares > 0").reset_index(drop=True)
    log.append(f"  ✅ {len(twse_shares)} 檔")

    # ── 上市每日資料 ──────────────────────────────────────
    log.append("【TWSE 日資料】")
    twse_frames = []
    for d in weekdays:
        url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json&date={d}"
        try:
            resp = requests.get(url, timeout=15, headers=HEADERS, verify=False)
            data = resp.json()
            stat = data.get("stat", "?")
            rows = len(data.get("data", []))
            log.append(f"  {d}：stat={stat}，{rows} 筆")
            if stat == "OK" and rows > 50:
                df = pd.DataFrame(data["data"], columns=data["fields"])
                df["date"] = pd.to_datetime(d, format="%Y%m%d")
                twse_frames.append(df)
        except Exception as e:
            log.append(f"  {d}：錯誤 {e}")
        if len(twse_frames) >= NEED:
            break
        time.sleep(0.5)

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
    log.append(f"  ✅ 上市整合：{twse['stock_id'].nunique()} 檔")

    # ── 上櫃每日資料（嘗試新舊兩種 API）────────────────────
    log.append("【TPEX 日資料（舊 API）】")
    TPEX_COLS = [
        "stock_id","stock_name","close_str","change",
        "open_str","high","low","vol_str","amount","trades",
        "bid_p","bid_v","ask_p","ask_v","shares_str","limit_up","limit_down"
    ]
    tpex_frames = []

    for d in weekdays:
        try:
            rows = fetch_tpex_old(d, log)
            if len(rows) > 50:
                n  = len(rows[0])
                df = pd.DataFrame(rows, columns=TPEX_COLS[:n])
                df["date"] = pd.to_datetime(d, format="%Y%m%d")
                tpex_frames.append(df)
        except Exception as e:
            log.append(f"    舊API {d} 例外：{e}")
        if len(tpex_frames) >= NEED:
            break
        time.sleep(0.5)

    # ── 舊 API 失敗，改用新 API ──────────────────────────
    if not tpex_frames:
        log.append("【TPEX 日資料（新 OpenAPI）】")
        new_frames = []
        for d in weekdays:
            try:
                data = fetch_tpex_new(d, log)
                if len(data) > 50:
                    df = pd.DataFrame(data)
                    df["date"] = pd.to_datetime(d, format="%Y%m%d")
                    new_frames.append(df)
                    log.append(f"    新API {d} 欄位：{list(df.columns[:8])}")
            except Exception as e:
                log.append(f"    新API {d} 例外：{e}")
            if len(new_frames) >= NEED:
                break
            time.sleep(0.5)

        if new_frames:
            # 新 API 欄位對應
            tpex_new = pd.concat(new_frames, ignore_index=True)
            log.append(f"    新 API 全部欄位：{list(tpex_new.columns)}")

            # 嘗試對應欄位（欄位名稱以實際 log 為準）
            col_map = {
                "SecuritiesCompanyCode": "stock_id",
                "CompanyName": "stock_name",
                "Close": "close_str",
                "Open": "open_str",
                "TradeVolume": "vol_str",
                "IssuedShares": "shares_str",
            }
            tpex_new = tpex_new.rename(columns={k:v for k,v in col_map.items() if k in tpex_new.columns})
            tpex_new["stock_id"] = tpex_new["stock_id"].astype(str).str.strip()
            tpex_new["volume"]   = clean_num(tpex_new.get("vol_str", pd.Series(dtype=str)))
            tpex_new["shares"]   = clean_num(tpex_new.get("shares_str", pd.Series(dtype=str)))
            tpex_new["open"]     = clean_num(tpex_new.get("open_str", pd.Series(dtype=str)))
            tpex_new["close"]    = clean_num(tpex_new.get("close_str", pd.Series(dtype=str)))
            tpex_new["market"]   = "上櫃"
            tpex_new = tpex_new.dropna(subset=["volume","shares","open","close"])
            tpex_new = tpex_new.query("volume>0 and shares>0 and close>0").copy()
            tpex_new["turnover_rate"] = (tpex_new["volume"] / tpex_new["shares"]) * 100
            tpex_frames_final = tpex_new
            log.append(f"  ✅ 上櫃整合（新API）：{tpex_new['stock_id'].nunique()} 檔")
        else:
            # 兩個 API 都失敗，只用上市資料
            log.append("⚠️ TPEX 兩種 API 均失敗，僅使用上市資料")
            KEEP = ["stock_id","stock_name","date","open","close",
                    "volume","shares","turnover_rate","market"]
            df = twse[KEEP].copy()
            df = df.sort_values(["stock_id","date"]).reset_index(drop=True)
            return df, log, ["只有上市資料，上櫃 API 目前無法取得"]
    else:
        tpex_raw = pd.concat(tpex_frames, ignore_index=True)
        tpex_raw["stock_id"] = tpex_raw["stock_id"].str.strip()
        tpex_raw["volume"]   = clean_num(tpex_raw["vol_str"])
        tpex_raw["shares"]   = clean_num(tpex_raw["shares_str"])
        tpex_raw["open"]     = clean_num(tpex_raw["open_str"])
        tpex_raw["close"]    = clean_num(tpex_raw["close_str"])
        tpex_raw["market"]   = "上櫃"
        tpex_frames_final = tpex_raw.dropna(subset=["volume","shares","open","close"])
        tpex_frames_final = tpex_frames_final.query("volume>0 and shares>0 and close>0").copy()
        tpex_frames_final["turnover_rate"] = (tpex_frames_final["volume"] / tpex_frames_final["shares"]) * 100
        log.append(f"  ✅ 上櫃整合（舊API）：{tpex_frames_final['stock_id'].nunique()} 檔")

    KEEP = ["stock_id","stock_name","date","open","close",
            "volume","shares","turnover_rate","market"]
    df = pd.concat([twse[KEEP], tpex_frames_final[KEEP]], ignore_index=True)
    df = df.sort_values(["stock_id","date"]).reset_index(drop=True)
    return df, log, []

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
            st.success(f"✅ 資料載入完成：{df['stock_id'].nunique()} 檔 × {df['date'].nunique()} 天（最新：{latest_available}）｜市場：{' / '.join(markets_in_df)}")
            for w in warnings_list:
                st.warning(f"⚠️ {w}")
            with st.expander("🔍 資料抓取 log（點此展開）"):
                st.text("\n".join(log))
        except ValueError as e:
            msg    = str(e)
            detail = msg.split("|")[1] if "|" in msg else ""
            st.error(f"❌ {msg.split('|')[0]}")
            if detail:
                with st.expander("🔍 詳細 log"):
                    st.text(detail)
            st.info("💡 請點左側「🗑️ 清除快取重新抓資料」後再試")
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
