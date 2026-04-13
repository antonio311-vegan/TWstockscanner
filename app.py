# ============================================================
# 📊 台股掃描器 v1
# 功能一：主力進場訊號（日線週轉率）
# 功能二：三刀流（60分K，20/60/240MA）
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import time
import warnings
from datetime import datetime, timedelta

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

HEADERS = {
    "User-Agent"      : "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept"          : "application/json, text/javascript, */*; q=0.01",
    "Accept-Language" : "zh-TW,zh;q=0.9",
    "Referer"         : "https://www.tpex.org.tw/",
}

st.set_page_config(page_title="台股掃描器", page_icon="📊", layout="wide")
st.title("📊 台股掃描器")
tab1, tab2 = st.tabs(["🎯 主力進場訊號", "⚔️ 三刀流（60分K）"])

# ════════════════════════════════════════════════════════════
# 共用工具函數
# ════════════════════════════════════════════════════════════

def clean_num(s):
    if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
    return pd.to_numeric(
        pd.Series(s).astype(str).str.replace(",","").str.replace(" ","").str.strip(),
        errors="coerce"
    )

def get_weekdays(n=30):
    dates, d = [], datetime.today()
    for _ in range(n):
        if d.weekday() < 5: dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates

# ════════════════════════════════════════════════════════════
# ═══════════════ TAB 1：主力進場訊號 ════════════════════════
# ════════════════════════════════════════════════════════════

with tab1:
    st.subheader("🎯 主力進場訊號掃描器")
    st.caption("沉寂股突然爆量 → 主力可能進場布局")

    with st.expander("📋 三訊號說明"):
        c1,c2,c3 = st.columns(3)
        c1.info("**訊號一**\n\n五日均週轉率 < 1%\n\n沉寂冷門股，沒人在玩")
        c2.info("**訊號二**\n\n今日週轉率 ≥ 2.5%\n且為五日均值 3 倍以上\n\n主力突然進場")
        c3.info("**訊號三**\n\n今日量為五日均量 2～5 倍\n\n量能健康放大")

    col_l, col_r = st.columns([1, 3])
    with col_l:
        st.markdown("**掃描參數**")
        t1_v = st.slider("訊號一：五日均週轉上限(%)", 0.5, 2.0, 1.0, 0.1, key="t1")
        t2_v = st.slider("訊號二：今日週轉下限(%)",   1.5, 5.0, 2.5, 0.1, key="t2")
        tm_v = st.slider("訊號二：週轉倍數下限",       2.0, 5.0, 3.0, 0.5, key="tm")
        vm_v = st.slider("訊號三：量比下限",           1.0, 3.0, 2.0, 0.5, key="vm")
        vx_v = st.slider("訊號三：量比上限",           3.0, 8.0, 5.0, 0.5, key="vx")
        mk_v = st.multiselect("市場", ["上市","上櫃"], default=["上市","上櫃"], key="mk")
        if st.button("🗑️ 清除快取", key="clr1"):
            st.cache_data.clear(); st.success("已清除")
        run1 = st.button("🚀 開始掃描", type="primary", use_container_width=True, key="run1")

    with col_r:
        if run1:
            # ── 取得資料 ──────────────────────────────────
            @st.cache_data(ttl=1800)
            def get_main_data():
                log = []; NEED = 8; wdays = get_weekdays()
                # 上市發行股數
                r = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                                  timeout=15, headers=HEADERS, verify=False)
                raw = pd.DataFrame(r.json())
                col = [c for c in raw.columns if "發行" in c and "股" in c][0]
                sh  = raw[["公司代號",col]].copy()
                sh.columns = ["stock_id","shares"]
                sh["stock_id"] = sh["stock_id"].str.strip()
                sh["shares"]   = clean_num(sh["shares"])
                sh = sh.dropna().query("shares>0").reset_index(drop=True)
                log.append(f"上市發行股數：{len(sh)} 檔")
                # 上市日資料
                twse_f = []
                for d in wdays:
                    url = f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json&date={d}"
                    try:
                        resp = requests.get(url, timeout=15, headers=HEADERS, verify=False)
                        data = resp.json()
                        if data.get("stat")=="OK" and len(data.get("data",[]))>50:
                            df = pd.DataFrame(data["data"], columns=data["fields"])
                            df["date"] = pd.to_datetime(d, format="%Y%m%d")
                            twse_f.append(df); log.append(f"TWSE {d}：{len(df)} 筆 ✅")
                    except Exception as e: log.append(f"TWSE {d}：{e}")
                    if len(twse_f)>=NEED: break
                    time.sleep(0.4)
                if not twse_f: raise ValueError("TWSE_EMPTY|"+"\n".join(log))
                twse = pd.concat(twse_f, ignore_index=True)
                twse = twse.rename(columns={"證券代號":"stock_id","證券名稱":"stock_name",
                    "成交股數":"vol_str","開盤價":"open_str","收盤價":"close_str"})
                twse["stock_id"] = twse["stock_id"].str.strip()
                twse["volume"]   = clean_num(twse["vol_str"])
                twse["open"]     = clean_num(twse["open_str"])
                twse["close"]    = clean_num(twse["close_str"])
                twse["market"]   = "上市"
                twse = twse.merge(sh, on="stock_id", how="inner")
                twse = twse.dropna(subset=["volume","shares","open","close"])
                twse = twse.query("volume>0 and shares>0 and close>0").copy()
                twse["turnover_rate"] = twse["volume"]/twse["shares"]*100
                log.append(f"上市整合：{twse['stock_id'].nunique()} 檔 ✅")
                # 上櫃
                TPEX_COLS = ["stock_id","stock_name","close_str","change","open_str","high","low",
                             "vol_str","amount","trades","bid_p","bid_v","ask_p","ask_v","shares_str","limit_up","limit_down"]
                tpex_f = []; warn = []
                for d in wdays:
                    dt  = datetime.strptime(d,"%Y%m%d")
                    roc = f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"
                    done = False
                    for url in [
                        f"https://www.tpex.org.tw/web/stock/aftertrading/all_daily_info/mpsas_result.php?l=zh-tw&o=json&d={roc}&s=0,asc",
                        f"https://openapi.tpex.org.tw/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8",
                        f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8",
                    ]:
                        try:
                            sess = requests.Session(); sess.headers.update(HEADERS)
                            try: sess.get("https://www.tpex.org.tw/", timeout=5, verify=False)
                            except: pass
                            resp = sess.get(url, timeout=12, verify=False)
                            raw2 = resp.text.strip()
                            if not raw2 or raw2[0] not in "[{": continue
                            data = resp.json()
                            rows = data.get("aaData") or (data if isinstance(data,list) else [])
                            if len(rows)>50:
                                if isinstance(rows[0], list):
                                    n = len(rows[0])
                                    df = pd.DataFrame(rows, columns=TPEX_COLS[:n])
                                    df["volume"] = clean_num(df["vol_str"])
                                    df["shares"] = clean_num(df["shares_str"])
                                    df["open"]   = clean_num(df["open_str"])
                                    df["close"]  = clean_num(df["close_str"])
                                else:
                                    df = pd.DataFrame(rows)
                                    df = df.loc[:, ~df.columns.duplicated()]
                                    FM = {"SecuritiesCompanyCode":"stock_id","CompanyName":"stock_name",
                                          "Close":"close","Open":"open","TradeVolume":"volume","IssuedShares":"shares"}
                                    df = df.rename(columns={k:v for k,v in FM.items() if k in df.columns})
                                    for c in ["volume","shares","open","close"]:
                                        if c in df.columns: df[c] = clean_num(df[c])
                                    if "stock_name" not in df.columns: df["stock_name"] = df.get("stock_id","")
                                df["date"] = pd.to_datetime(d, format="%Y%m%d")
                                df["market"] = "上櫃"
                                df["stock_id"] = df["stock_id"].astype(str).str.strip()
                                tpex_f.append(df); log.append(f"TPEX {d}：{len(df)} 筆 ✅")
                                done = True; break
                        except: pass
                    if not done: log.append(f"TPEX {d}：失敗")
                    if len(tpex_f)>=NEED: break
                    time.sleep(0.5)
                KEEP = ["stock_id","stock_name","date","open","close","volume","shares","turnover_rate","market"]
                if tpex_f:
                    tpex_all = pd.concat(tpex_f, ignore_index=True)
                    tpex_all = tpex_all.dropna(subset=["volume","shares","open","close"])
                    tpex_all = tpex_all.query("volume>0 and shares>0 and close>0").copy()
                    tpex_all["turnover_rate"] = tpex_all["volume"]/tpex_all["shares"]*100
                    log.append(f"上櫃整合：{tpex_all['stock_id'].nunique()} 檔 ✅")
                    df_all = pd.concat([twse[KEEP], tpex_all[KEEP]], ignore_index=True)
                else:
                    warn.append("上櫃資料暫時無法取得，本次只掃描上市")
                    df_all = twse[KEEP].copy()
                return df_all.sort_values(["stock_id","date"]).reset_index(drop=True), log, warn

            with st.spinner("📡 抓取資料中..."):
                try:
                    df, log, warns = get_main_data()
                    st.success(f"✅ {df['stock_id'].nunique()} 檔 × {df['date'].nunique()} 天｜最新：{df['date'].max().strftime('%Y-%m-%d')}｜市場：{' / '.join(df['market'].unique())}")
                    for w in warns: st.warning(f"⚠️ {w}")
                    with st.expander("🔍 log"): st.text("\n".join(log))
                except Exception as e:
                    import traceback
                    st.error(f"❌ {e}")
                    with st.expander("詳細錯誤"): st.text(traceback.format_exc())
                    st.stop()

            # ── 三訊號掃描 ────────────────────────────────
            latest = df["date"].max()
            df2    = df[df["market"].isin(mk_v)]
            results = []
            for sid, grp in df2.groupby("stock_id"):
                grp = grp.sort_values("date")
                tr  = grp[grp["date"]==latest]
                if tr.empty: continue
                p5  = grp[grp["date"]<latest].tail(5)
                if len(p5)<5: continue
                row    = tr.iloc[0]
                t_now  = row["turnover_rate"]; t_avg = p5["turnover_rate"].mean()
                v_now  = row["volume"];         v_avg = p5["volume"].mean()
                if t_avg<=0 or v_avg<=0: continue
                tr_    = t_now/t_avg; vr_ = v_now/v_avg
                if t_avg<t1_v and t_now>=t2_v and tr_>=tm_v and vm_v<=vr_<=vx_v:
                    chg = round(((row["close"]-row["open"])/row["open"])*100,2) if row["open"]>0 else 0
                    results.append({"市場":row["market"],"代號":sid,"名稱":row.get("stock_name",sid),
                        "收盤價":row["close"],"當日漲跌(%)":chg,
                        "五日均週轉(%)":round(t_avg,3),"今日週轉(%)":round(t_now,3),
                        "週轉率倍數":round(tr_,1),"量比":round(vr_,1)})
            rdf = pd.DataFrame(results)
            if len(rdf)>0: rdf = rdf.sort_values("週轉率倍數",ascending=False).reset_index(drop=True)

            st.markdown(f"### 🎯 掃描結果 — {latest.strftime('%Y-%m-%d')}")
            c1,c2,c3 = st.columns(3)
            c1.metric("符合總數", f"{len(rdf)} 檔")
            c2.metric("上市", f"{len(rdf[rdf['市場']=='上市']) if len(rdf)>0 else 0} 檔")
            c3.metric("上櫃", f"{len(rdf[rdf['市場']=='上櫃']) if len(rdf)>0 else 0} 檔")

            if len(rdf)>0:
                def cc(v): return f"color:{'red' if v>0 else 'green' if v<0 else 'gray'}"
                st.dataframe(rdf.style.applymap(cc, subset=["當日漲跌(%)"]), use_container_width=True, height=450)
                csv = rdf.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("💾 下載 CSV", csv, f"主力訊號_{latest.strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
            else:
                td = df[df["date"]==latest]
                st.info("此交易日無符合三條件的股票")
                cc2 = st.columns(4)
                cc2[0].metric("掃描股數", f"{len(td)} 檔")
                cc2[1].metric("週轉率中位數", f"{td['turnover_rate'].median():.2f}%")
                cc2[2].metric("週轉率最大", f"{td['turnover_rate'].max():.2f}%")
                cc2[3].metric("週轉>2.5%股數", f"{(td['turnover_rate']>=2.5).sum()} 檔")
        else:
            st.info("👈 設定參數後按「開始掃描」")

# ════════════════════════════════════════════════════════════
# ═══════════════ TAB 2：三刀流 60分K ════════════════════════
# ════════════════════════════════════════════════════════════

with tab2:
    st.subheader("⚔️ 三刀流掃描器（60分K）")

    with st.expander("📖 三刀流策略說明（點此展開）"):
        st.markdown("""
| 角色 | 均線 | 職責 |
|------|------|------|
| 👑 劉備 | **240MA** | 決定大方向，多空分水嶺 |
| ⚔️ 關羽 | **60MA** | 進出場節奏，抓轉折切入點 |
| 🔥 張飛 | **20MA** | 停利控風險，不讓戰果吐回 |

**四種信號：**
- 🔴 **三刀做多**：站上劉備＋關羽剛穿越張飛向上＋張飛正斜率 → 全力做多
- 🟡 **空頭反彈**：跌破劉備 但 站上關羽 → 短打反彈多
- 🟣 **多頭修正空**：站上劉備 但 跌破關羽 → 修正空
- 🔵 **三刀做空**：跌破劉備＋關羽向下穿越張飛＋張飛負斜率 → 做空
        """)

    col_l2, col_r2 = st.columns([1, 3])

    with col_l2:
        st.markdown("**掃描設定**")
        signal_types = st.multiselect("掃描信號類型",
            ["🔴 三刀做多","🟡 空頭反彈多","🟣 多頭修正空","🔵 三刀做空"],
            default=["🔴 三刀做多","🟡 空頭反彈多"],
            key="sig_types"
        )
        cross_bars = st.slider("穿越發生於最近幾根K棒內", 1, 5, 2, key="cross_bars")
        st.caption("設 2 = 最近 2 根 60分K 內發生穿越")

        ma_slope_bars = st.slider("張飛斜率判斷回看K棒數", 2, 10, 3, key="slope_bars")

        if st.button("🗑️ 清除三刀快取", key="clr2"):
            st.cache_data.clear(); st.success("已清除")

        run2 = st.button("⚔️ 開始三刀掃描", type="primary", use_container_width=True, key="run2")
        st.caption("⚠️ 約 1800 檔，預計 3～8 分鐘")

    with col_r2:
        if run2:

            # ── Step1：取得股票清單 ─────────────────────────
            @st.cache_data(ttl=86400)
            def get_stock_list():
                """取得上市＋上櫃股票代號"""
                stocks = []
                # 上市
                try:
                    r = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                                     timeout=15, headers=HEADERS, verify=False)
                    df = pd.DataFrame(r.json())
                    ids = df["公司代號"].str.strip().tolist()
                    stocks += [(i, i+".TW", "上市") for i in ids if i.isdigit()]
                except: pass
                # 上櫃（嘗試多個端點）
                for url in [
                    "https://openapi.tpex.org.tw/v1/tpex_mainboard_peratio_analysis",
                    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis",
                ]:
                    try:
                        r = requests.get(url, timeout=15, headers=HEADERS, verify=False)
                        raw = r.text.strip()
                        if raw and raw[0] in "[{":
                            data = r.json()
                            rows = data if isinstance(data,list) else data.get("aaData",[])
                            if rows:
                                for row in rows:
                                    sid = str(row.get("SecuritiesCompanyCode") or row.get("Code") or "").strip()
                                    if sid and sid.isdigit():
                                        stocks.append((sid, sid+".TWO", "上櫃"))
                                break
                    except: pass
                # 若上櫃 API 失敗，用備用清單（硬編碼前幾百個常見上櫃股）
                if not any(m=="上櫃" for _,_,m in stocks):
                    # 上櫃代號通常在 3000-9999 但需要實際清單，先跳過
                    pass
                return list({s[0]:s for s in stocks}.values())  # 去重

            with st.spinner("📋 取得股票清單..."):
                stock_list = get_stock_list()
                twse_cnt = sum(1 for _,_,m in stock_list if m=="上市")
                tpex_cnt = sum(1 for _,_,m in stock_list if m=="上櫃")
                st.info(f"共 {len(stock_list)} 檔（上市 {twse_cnt}，上櫃 {tpex_cnt}）")

            # ── Step2：批次下載 60分K ───────────────────────
            def calc_ma_signals(df_price, cross_n, slope_n):
                """
                計算 20/60/240 MA，判斷四種三刀信號
                回傳 dict 或 None
                """
                if len(df_price) < 260:
                    return None

                c = df_price["Close"].values
                ma20  = pd.Series(c).rolling(20).mean().values
                ma60  = pd.Series(c).rolling(60).mean().values
                ma240 = pd.Series(c).rolling(240).mean().values

                # 最新值
                price = c[-1]
                m20   = ma20[-1];  m60  = ma60[-1];  m240 = ma240[-1]
                if np.isnan(m20) or np.isnan(m60) or np.isnan(m240):
                    return None

                # 張飛（20MA）斜率：比較最新 vs slope_n 根前
                slope_20 = m20 - ma20[-(slope_n+1)] if len(ma20)>slope_n else 0
                pos_slope = slope_20 > 0
                neg_slope = slope_20 < 0

                # 穿越偵測：在最近 cross_n 根 K 棒內
                def cross_up(fast, slow, n):
                    for i in range(1, n+1):
                        idx = -(i+1); idx2 = -i
                        if idx < -len(fast): break
                        if fast[idx] < slow[idx] and fast[idx2] >= slow[idx2]:
                            return True
                    return False

                def cross_down(fast, slow, n):
                    for i in range(1, n+1):
                        idx = -(i+1); idx2 = -i
                        if idx < -len(fast): break
                        if fast[idx] > slow[idx] and fast[idx2] <= slow[idx2]:
                            return True
                    return False

                # 60MA 上穿 20MA（關羽穿越張飛向上）
                ma60_cross_up20   = cross_up(ma60,  ma20,  cross_n)
                # 60MA 下穿 20MA
                ma60_cross_down20 = cross_down(ma60, ma20, cross_n)
                # 價格站上/跌破 60MA
                price_cross_up60  = cross_up(c, ma60, cross_n)
                price_cross_down60= cross_down(c, ma60, cross_n)

                # 判斷信號
                above_240 = price > m240
                above_60  = price > m60

                signal = None

                # 🔴 三刀做多：站上劉備 + 60MA上穿20MA + 張飛正斜率
                if "🔴 三刀做多" in signal_types:
                    if above_240 and ma60_cross_up20 and pos_slope:
                        signal = "🔴 三刀做多"

                # 🟡 空頭反彈：跌破劉備 + 價格站上60MA
                if signal is None and "🟡 空頭反彈多" in signal_types:
                    if not above_240 and price_cross_up60:
                        signal = "🟡 空頭反彈多"

                # 🟣 多頭修正空：站上劉備 + 價格跌破60MA
                if signal is None and "🟣 多頭修正空" in signal_types:
                    if above_240 and price_cross_down60:
                        signal = "🟣 多頭修正空"

                # 🔵 三刀做空：跌破劉備 + 60MA下穿20MA + 張飛負斜率
                if signal is None and "🔵 三刀做空" in signal_types:
                    if not above_240 and ma60_cross_down20 and neg_slope:
                        signal = "🔵 三刀做空"

                if signal is None:
                    return None

                return {
                    "信號"    : signal,
                    "收盤價"  : round(price, 2),
                    "20MA"    : round(m20, 2),
                    "60MA"    : round(m60, 2),
                    "240MA"   : round(m240, 2),
                    "張飛斜率": "⬆️ 正" if pos_slope else "⬇️ 負",
                    "劉備位置": "✅ 站上" if above_240 else "❌ 跌破",
                    "關羽位置": "✅ 站上" if above_60  else "❌ 跌破",
                }

            # 批次掃描
            results2  = []
            total     = len(stock_list)
            prog_bar  = st.progress(0, text="⚔️ 掃描中...")
            status_tx = st.empty()
            err_count = 0

            BATCH = 20   # 每批下載幾檔
            for batch_start in range(0, total, BATCH):
                batch    = stock_list[batch_start:batch_start+BATCH]
                tickers  = [yf_code for _, yf_code, _ in batch]
                mkt_map  = {yf_code: (sid, mkt) for sid, yf_code, mkt in batch}

                pct = int(batch_start/total*100)
                prog_bar.progress(pct/100, text=f"⚔️ 掃描 {batch_start}/{total}...")
                status_tx.caption(f"正在處理：{', '.join(t.split('.')[0] for t in tickers[:5])} ...")

                try:
                    raw = yf.download(
                        tickers,
                        period="60d",
                        interval="60m",
                        group_by="ticker",
                        auto_adjust=True,
                        progress=False,
                        threads=True,
                    )
                except Exception as e:
                    err_count += 1; continue

                for yf_code in tickers:
                    sid, mkt = mkt_map[yf_code]
                    try:
                        if len(tickers) == 1:
                            df_p = raw
                        else:
                            df_p = raw[yf_code] if yf_code in raw.columns.get_level_values(0) else None
                        if df_p is None or df_p.empty or "Close" not in df_p.columns:
                            continue
                        df_p = df_p.dropna(subset=["Close"])
                        res  = calc_ma_signals(df_p, cross_bars, ma_slope_bars)
                        if res:
                            res["代號"] = sid
                            res["市場"] = mkt
                            results2.append(res)
                    except:
                        pass

                time.sleep(0.3)

            prog_bar.progress(1.0, text="✅ 掃描完成")
            status_tx.empty()

            # ── 顯示結果 ──────────────────────────────────
            if results2:
                rdf2 = pd.DataFrame(results2)
                # 取得股票名稱
                try:
                    name_r = requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                                          timeout=10, headers=HEADERS, verify=False)
                    nm = pd.DataFrame(name_r.json())[["公司代號","公司簡稱"]].copy()
                    nm.columns = ["代號","名稱"]
                    nm["代號"] = nm["代號"].str.strip()
                    rdf2 = rdf2.merge(nm, on="代號", how="left")
                    rdf2["名稱"] = rdf2.get("名稱", rdf2["代號"])
                except:
                    rdf2["名稱"] = rdf2["代號"]

                col_order = ["信號","市場","代號","名稱","收盤價","20MA","60MA","240MA","張飛斜率","劉備位置","關羽位置"]
                rdf2 = rdf2[[c for c in col_order if c in rdf2.columns]]

                # 依信號分組顯示
                sig_order = ["🔴 三刀做多","🟡 空頭反彈多","🟣 多頭修正空","🔵 三刀做空"]
                st.markdown(f"### ⚔️ 三刀流掃描結果｜{datetime.now().strftime('%Y-%m-%d %H:%M')}")
                c1,c2,c3,c4 = st.columns(4)
                for col, sig in zip([c1,c2,c3,c4], sig_order):
                    n = len(rdf2[rdf2["信號"]==sig])
                    col.metric(sig, f"{n} 檔")

                for sig in sig_order:
                    sub = rdf2[rdf2["信號"]==sig]
                    if len(sub)>0:
                        st.markdown(f"#### {sig}（{len(sub)} 檔）")
                        st.dataframe(sub.drop(columns=["信號"]), use_container_width=True)

                csv2 = rdf2.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("💾 下載結果 CSV", csv2,
                    f"三刀流_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    "text/csv", use_container_width=True)

                if err_count > 0:
                    st.caption(f"⚠️ {err_count} 批次下載失敗（網路逾時），結果僅供參考")
            else:
                st.info("目前無符合三刀流條件的股票，可調整穿越根數後重試")

        else:
            st.markdown("""
**使用說明：**
1. 左側選擇要掃描的信號類型
2. 調整穿越判斷的 K 棒數（建議 2～3）
3. 按「⚔️ 開始三刀掃描」

> **約需 3～8 分鐘**掃描全市場 1800 檔
> 掃描結果為 60 分 K 最新狀態，請搭配走勢圖確認
            """)
            st.markdown("""
---
**三刀流信號類型：**
- 🔴 **三刀做多**：站上劉備（240MA）＋ 關羽上穿張飛（60MA上穿20MA）＋ 張飛正斜率
- 🟡 **空頭反彈多**：跌破劉備 ＋ 價格站上關羽
- 🟣 **多頭修正空**：站上劉備 ＋ 價格跌破關羽
- 🔵 **三刀做空**：跌破劉備 ＋ 關羽下穿張飛 ＋ 張飛負斜率
            """)
