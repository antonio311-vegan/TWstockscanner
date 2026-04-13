# ============================================================
# 📊 台股掃描器 v3（修正三刀流邏輯，符合刀神圖示）
# 功能一：主力進場訊號
# 功能二：三刀流（60分K）+ AI 推薦
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import time
import json
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
# 共用工具
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
# AI 推薦
# ════════════════════════════════════════════════════════════

def ai_recommend(df_results: pd.DataFrame, scan_type: str) -> dict:
    if df_results.empty: return None
    rows_str = df_results.head(20).to_string(index=False)
    prompt = f"""你是一位有20年經驗的台股專業投資人，精通技術分析與籌碼分析。

以下是三刀流策略（60分K，小藍20MA/小綠60MA/小橘240MA）掃描出的股票清單：
掃描信號：{scan_type}

{rows_str}

請以專業角度選出【最值得優先關注的一檔】。

只回覆 JSON，不加任何其他文字：
{{
  "stock_id": "股票代號",
  "name": "股票名稱",
  "signal": "信號類型",
  "reason": "推薦理由（50字以內，繁體中文）",
  "key_point": "操作重點（30字以內，繁體中文）",
  "confidence": "高/中/低",
  "risk": "高/中/低"
}}"""
    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"Content-Type": "application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":500,
                  "messages":[{"role":"user","content":prompt}]},
            timeout=30
        )
        text = resp.json()["content"][0]["text"].strip()
        text = text.replace("```json","").replace("```","").strip()
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}

# ════════════════════════════════════════════════════════════
# TAB 1：主力進場訊號
# ════════════════════════════════════════════════════════════

with tab1:
    st.subheader("🎯 主力進場訊號掃描器")
    st.caption("沉寂股突然爆量 → 主力可能進場布局")

    with st.expander("📋 三訊號說明"):
        c1,c2,c3 = st.columns(3)
        c1.info("**訊號一**\n\n五日均週轉率 < 1%\n\n沉寂冷門股")
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
            @st.cache_data(ttl=1800)
            def get_main_data():
                log=[]; NEED=8; wdays=get_weekdays()
                r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                                timeout=15,headers=HEADERS,verify=False)
                raw=pd.DataFrame(r.json())
                col=[c for c in raw.columns if "發行" in c and "股" in c][0]
                sh=raw[["公司代號",col]].copy(); sh.columns=["stock_id","shares"]
                sh["stock_id"]=sh["stock_id"].str.strip(); sh["shares"]=clean_num(sh["shares"])
                sh=sh.dropna().query("shares>0").reset_index(drop=True)
                log.append(f"上市發行股數：{len(sh)} 檔")
                twse_f=[]
                for d in wdays:
                    url=f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json&date={d}"
                    try:
                        resp=requests.get(url,timeout=15,headers=HEADERS,verify=False)
                        data=resp.json()
                        if data.get("stat")=="OK" and len(data.get("data",[]))>50:
                            df=pd.DataFrame(data["data"],columns=data["fields"])
                            df["date"]=pd.to_datetime(d,format="%Y%m%d")
                            twse_f.append(df); log.append(f"TWSE {d}：{len(df)} 筆 ✅")
                    except Exception as e: log.append(f"TWSE {d}：{e}")
                    if len(twse_f)>=NEED: break
                    time.sleep(0.4)
                if not twse_f: raise ValueError("TWSE_EMPTY|"+"\n".join(log))
                twse=pd.concat(twse_f,ignore_index=True)
                twse=twse.rename(columns={"證券代號":"stock_id","證券名稱":"stock_name",
                    "成交股數":"vol_str","開盤價":"open_str","收盤價":"close_str"})
                twse["stock_id"]=twse["stock_id"].str.strip()
                twse["volume"]=clean_num(twse["vol_str"]); twse["open"]=clean_num(twse["open_str"])
                twse["close"]=clean_num(twse["close_str"]); twse["market"]="上市"
                twse=twse.merge(sh,on="stock_id",how="inner")
                twse=twse.dropna(subset=["volume","shares","open","close"])
                twse=twse.query("volume>0 and shares>0 and close>0").copy()
                twse["turnover_rate"]=twse["volume"]/twse["shares"]*100
                log.append(f"上市整合：{twse['stock_id'].nunique()} 檔 ✅")
                TPEX_COLS=["stock_id","stock_name","close_str","change","open_str","high","low",
                           "vol_str","amount","trades","bid_p","bid_v","ask_p","ask_v","shares_str","limit_up","limit_down"]
                tpex_f=[]; warn=[]
                for d in wdays:
                    dt=datetime.strptime(d,"%Y%m%d"); roc=f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"
                    done=False
                    for url in [
                        f"https://www.tpex.org.tw/web/stock/aftertrading/all_daily_info/mpsas_result.php?l=zh-tw&o=json&d={roc}&s=0,asc",
                        f"https://openapi.tpex.org.tw/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8",
                        f"https://www.tpex.org.tw/openapi/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8",
                    ]:
                        try:
                            sess=requests.Session(); sess.headers.update(HEADERS)
                            try: sess.get("https://www.tpex.org.tw/",timeout=5,verify=False)
                            except: pass
                            resp=sess.get(url,timeout=12,verify=False); raw2=resp.text.strip()
                            if not raw2 or raw2[0] not in "[{": continue
                            data=resp.json()
                            rows=data.get("aaData") or (data if isinstance(data,list) else [])
                            if len(rows)>50:
                                if isinstance(rows[0],list):
                                    n=len(rows[0]); df=pd.DataFrame(rows,columns=TPEX_COLS[:n])
                                    df["volume"]=clean_num(df["vol_str"]); df["shares"]=clean_num(df["shares_str"])
                                    df["open"]=clean_num(df["open_str"]); df["close"]=clean_num(df["close_str"])
                                else:
                                    df=pd.DataFrame(rows); df=df.loc[:,~df.columns.duplicated()]
                                    FM={"SecuritiesCompanyCode":"stock_id","CompanyName":"stock_name",
                                        "Close":"close","Open":"open","TradeVolume":"volume","IssuedShares":"shares"}
                                    df=df.rename(columns={k:v for k,v in FM.items() if k in df.columns})
                                    for c in ["volume","shares","open","close"]:
                                        if c in df.columns: df[c]=clean_num(df[c])
                                    if "stock_name" not in df.columns: df["stock_name"]=df.get("stock_id","")
                                df["date"]=pd.to_datetime(d,format="%Y%m%d"); df["market"]="上櫃"
                                df["stock_id"]=df["stock_id"].astype(str).str.strip()
                                tpex_f.append(df); log.append(f"TPEX {d}：{len(df)} 筆 ✅")
                                done=True; break
                        except: pass
                    if not done: log.append(f"TPEX {d}：失敗")
                    if len(tpex_f)>=NEED: break
                    time.sleep(0.5)
                KEEP=["stock_id","stock_name","date","open","close","volume","shares","turnover_rate","market"]
                if tpex_f:
                    tpex_all=pd.concat(tpex_f,ignore_index=True)
                    tpex_all=tpex_all.dropna(subset=["volume","shares","open","close"])
                    tpex_all=tpex_all.query("volume>0 and shares>0 and close>0").copy()
                    tpex_all["turnover_rate"]=tpex_all["volume"]/tpex_all["shares"]*100
                    log.append(f"上櫃整合：{tpex_all['stock_id'].nunique()} 檔 ✅")
                    df_all=pd.concat([twse[KEEP],tpex_all[KEEP]],ignore_index=True)
                else:
                    warn.append("上櫃資料暫時無法取得，本次只掃描上市")
                    df_all=twse[KEEP].copy()
                return df_all.sort_values(["stock_id","date"]).reset_index(drop=True),log,warn

            with st.spinner("📡 抓取資料中..."):
                try:
                    df,log,warns=get_main_data()
                    st.success(f"✅ {df['stock_id'].nunique()} 檔 × {df['date'].nunique()} 天｜最新：{df['date'].max().strftime('%Y-%m-%d')}｜市場：{' / '.join(df['market'].unique())}")
                    for w in warns: st.warning(f"⚠️ {w}")
                    with st.expander("🔍 log"): st.text("\n".join(log))
                except Exception as e:
                    import traceback
                    st.error(f"❌ {e}")
                    with st.expander("詳細錯誤"): st.text(traceback.format_exc())
                    st.stop()

            latest=df["date"].max(); df2=df[df["market"].isin(mk_v)]; results=[]
            for sid,grp in df2.groupby("stock_id"):
                grp=grp.sort_values("date"); tr=grp[grp["date"]==latest]
                if tr.empty: continue
                p5=grp[grp["date"]<latest].tail(5)
                if len(p5)<5: continue
                row=tr.iloc[0]; t_now=row["turnover_rate"]; t_avg=p5["turnover_rate"].mean()
                v_now=row["volume"]; v_avg=p5["volume"].mean()
                if t_avg<=0 or v_avg<=0: continue
                tr_=t_now/t_avg; vr_=v_now/v_avg
                if t_avg<t1_v and t_now>=t2_v and tr_>=tm_v and vm_v<=vr_<=vx_v:
                    chg=round(((row["close"]-row["open"])/row["open"])*100,2) if row["open"]>0 else 0
                    results.append({"市場":row["market"],"代號":sid,"名稱":row.get("stock_name",sid),
                        "收盤價":row["close"],"當日漲跌(%)":chg,
                        "五日均週轉(%)":round(t_avg,3),"今日週轉(%)":round(t_now,3),
                        "週轉率倍數":round(tr_,1),"量比":round(vr_,1)})
            rdf=pd.DataFrame(results)
            if len(rdf)>0: rdf=rdf.sort_values("週轉率倍數",ascending=False).reset_index(drop=True)

            st.markdown(f"### 🎯 掃描結果 — {latest.strftime('%Y-%m-%d')}")
            c1,c2,c3=st.columns(3)
            c1.metric("符合總數",f"{len(rdf)} 檔")
            c2.metric("上市",f"{len(rdf[rdf['市場']=='上市']) if len(rdf)>0 else 0} 檔")
            c3.metric("上櫃",f"{len(rdf[rdf['市場']=='上櫃']) if len(rdf)>0 else 0} 檔")
            if len(rdf)>0:
                def cc(v): return f"color:{'red' if v>0 else 'green' if v<0 else 'gray'}"
                st.dataframe(rdf.style.applymap(cc,subset=["當日漲跌(%)"]),use_container_width=True,height=400)
                csv=rdf.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("💾 下載 CSV",csv,f"主力訊號_{latest.strftime('%Y%m%d')}.csv","text/csv",use_container_width=True)
            else:
                td=df[df["date"]==latest]; st.info("此交易日無符合三條件的股票")
                cc2=st.columns(4)
                cc2[0].metric("掃描股數",f"{len(td)} 檔")
                cc2[1].metric("週轉率中位數",f"{td['turnover_rate'].median():.2f}%")
                cc2[2].metric("週轉率最大",f"{td['turnover_rate'].max():.2f}%")
                cc2[3].metric("週轉>2.5%股數",f"{(td['turnover_rate']>=2.5).sum()} 檔")
        else:
            st.info("👈 設定參數後按「開始掃描」")

# ════════════════════════════════════════════════════════════
# TAB 2：三刀流（修正版，符合刀神圖示）
# ════════════════════════════════════════════════════════════

with tab2:
    st.subheader("⚔️ 刀神均線三刀流（60分K）")

    with st.expander("📖 三刀流策略說明（依刀神原版）"):
        st.markdown("""
| 角色 | 顏色 | 均線 | 職責 |
|------|------|------|------|
| 👑 劉備 | 🟠 小橘 | **240MA** | 決定方向：全站上偏多，全跌破偏空 |
| ⚔️ 關羽 | 🟢 小綠 | **60MA**  | 進出殺敵：站上做多，跌破做空 |
| 🔥 張飛 | 🔵 小藍 | **20MA**  | 收尾控場：負斜率多單下車，正斜率空單平倉 |

**四種進場信號：**
| 信號 | 條件 | 操作 |
|------|------|------|
| 🔴 **三刀做多** | 站上小橘(240) **且** 站上小綠(60) | 偏多全力進 |
| 🟡 **反彈做多** | 上小綠(60) **不上小橘**(240) | 短打反彈多 |
| 🟣 **修正做空** | 上小橘(240) **不上小綠**(60) | 修正空 |
| 🔵 **三刀做空** | 跌破小橘(240) **且** 跌破小綠(60) | 偏空全力進 |

**張飛（20MA）= 出場信號：**
- 小藍**負斜率** → 多單下車警示 ⚠️
- 小藍**正斜率** → 空單平倉警示 ⚠️
        """)

    col_l2, col_r2 = st.columns([1, 3])

    with col_l2:
        st.markdown("**掃描設定**")
        signal_types = st.multiselect("信號類型",
            ["🔴 三刀做多","🟡 反彈做多","🟣 修正做空","🔵 三刀做空"],
            default=["🔴 三刀做多","🟡 反彈做多"], key="sig_types")
        cross_bars = st.slider("穿越/突破發生於最近幾根K棒內", 1, 5, 2, key="cross_bars")
        slope_bars = st.slider("20MA斜率判斷回看K棒數",        2, 10, 3, key="slope_bars")
        show_ai    = st.toggle("🤖 AI 推薦最佳標的", value=True, key="show_ai")
        if st.button("🗑️ 清除三刀快取", key="clr2"):
            st.cache_data.clear(); st.success("已清除")
        run2 = st.button("⚔️ 開始三刀掃描", type="primary", use_container_width=True, key="run2")
        st.caption("⚠️ 全市場約 3～8 分鐘")

    with col_r2:
        if run2:

            @st.cache_data(ttl=86400)
            def get_stock_list():
                stocks=[]
                try:
                    r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                                   timeout=15,headers=HEADERS,verify=False)
                    df=pd.DataFrame(r.json())
                    ids=df["公司代號"].str.strip().tolist()
                    stocks+=[(i,i+".TW","上市") for i in ids if i.isdigit()]
                except: pass
                for url in [
                    "https://openapi.tpex.org.tw/v1/tpex_mainboard_peratio_analysis",
                    "https://www.tpex.org.tw/openapi/v1/tpex_mainboard_peratio_analysis",
                ]:
                    try:
                        r=requests.get(url,timeout=15,headers=HEADERS,verify=False)
                        raw=r.text.strip()
                        if raw and raw[0] in "[{":
                            data=r.json()
                            rows=data if isinstance(data,list) else data.get("aaData",[])
                            if rows:
                                for row in rows:
                                    sid=str(row.get("SecuritiesCompanyCode") or row.get("Code") or "").strip()
                                    if sid and sid.isdigit():
                                        stocks.append((sid,sid+".TWO","上櫃"))
                                break
                    except: pass
                return list({s[0]:s for s in stocks}.values())

            with st.spinner("📋 取得股票清單..."):
                stock_list=get_stock_list()
                twse_cnt=sum(1 for _,_,m in stock_list if m=="上市")
                tpex_cnt=sum(1 for _,_,m in stock_list if m=="上櫃")
                st.info(f"共 {len(stock_list)} 檔（上市 {twse_cnt}，上櫃 {tpex_cnt}）")

            # ── 三刀流信號計算（修正版）──────────────────────
            # 劉備小橘 = 240MA：決定方向
            # 關羽小綠 =  60MA：進出節奏
            # 張飛小藍 =  20MA：出場控風險（斜率方向）
            def calc_signals(df_p, cross_n, slope_n, sig_types):
                if len(df_p) < 260: return None
                c    = df_p["Close"].values
                ma20 = pd.Series(c).rolling(20).mean().values
                ma60 = pd.Series(c).rolling(60).mean().values
                ma240= pd.Series(c).rolling(240).mean().values

                price=c[-1]; m20=ma20[-1]; m60=ma60[-1]; m240=ma240[-1]
                if any(np.isnan(v) for v in [m20,m60,m240]): return None

                # 張飛小藍（20MA）斜率
                slope_20  = m20 - ma20[-(slope_n+1)] if len(ma20)>slope_n else 0
                pos_slope = slope_20 > 0
                neg_slope = slope_20 < 0

                # 穿越偵測（最近 cross_n 根）
                def cup(fast, slow, n):
                    for i in range(1, n+1):
                        if -(i+1) < -len(fast): break
                        if fast[-(i+1)] < slow[-(i+1)] and fast[-i] >= slow[-i]: return True
                    return False
                def cdn(fast, slow, n):
                    for i in range(1, n+1):
                        if -(i+1) < -len(fast): break
                        if fast[-(i+1)] > slow[-(i+1)] and fast[-i] <= slow[-i]: return True
                    return False

                # 位置判斷
                above240 = price > m240   # 劉備小橘
                above60  = price > m60    # 關羽小綠

                # 最近 cross_n 根內是否站上/跌破 60MA
                just_above60 = cup(c, ma60, cross_n)
                just_below60 = cdn(c, ma60, cross_n)

                # ── 四種信號（依刀神原版）────────────────────
                # 🔴 三刀做多：全站上（上小橘 + 上小綠）
                #   → 用「剛站上小綠」作為進場觸發（趨勢確認時機）
                # 🟡 反彈做多：上小綠不上小橘
                # 🟣 修正做空：上小橘不上小綠（剛跌破小綠）
                # 🔵 三刀做空：全跌破（跌破小橘 + 跌破小綠）

                signal = None

                if "🔴 三刀做多" in sig_types:
                    if above240 and above60 and just_above60:
                        signal = "🔴 三刀做多"

                if not signal and "🟡 反彈做多" in sig_types:
                    if not above240 and just_above60:
                        signal = "🟡 反彈做多"

                if not signal and "🟣 修正做空" in sig_types:
                    if above240 and just_below60:
                        signal = "🟣 修正做空"

                if not signal and "🔵 三刀做空" in sig_types:
                    if not above240 and not above60 and just_below60:
                        signal = "🔵 三刀做空"

                if not signal: return None

                # 張飛出場警示
                if signal in ["🔴 三刀做多","🟡 反彈做多"]:
                    zhang_warn = "⚠️ 負斜率，注意多單下車" if neg_slope else "✅ 正斜率，多頭有力"
                else:
                    zhang_warn = "⚠️ 正斜率，注意空單平倉" if pos_slope else "✅ 負斜率，空頭有力"

                return {
                    "信號"          : signal,
                    "收盤價"        : round(price, 2),
                    "小橘240MA"     : round(m240, 2),
                    "小綠60MA"      : round(m60,  2),
                    "小藍20MA"      : round(m20,  2),
                    "vs小橘240MA"   : "✅ 站上" if above240 else "❌ 跌破",
                    "vs小綠60MA"    : "✅ 站上" if above60  else "❌ 跌破",
                    "張飛警示"      : zhang_warn,
                }

            # ── 批次掃描 ──────────────────────────────────
            results2=[]; total=len(stock_list)
            prog=st.progress(0,"⚔️ 掃描中..."); status=st.empty(); err=0; BATCH=20

            for bs in range(0, total, BATCH):
                batch  = stock_list[bs:bs+BATCH]
                tickers= [yc for _,yc,_ in batch]
                mkt_map= {yc:(sid,mkt) for sid,yc,mkt in batch}
                prog.progress(int(bs/total*100)/100, f"⚔️ 掃描 {bs}/{total}...")
                status.caption(f"處理中：{', '.join(t.split('.')[0] for t in tickers[:5])} ...")
                try:
                    raw=yf.download(tickers,period="60d",interval="60m",
                        group_by="ticker",auto_adjust=True,progress=False,threads=True)
                except: err+=1; continue
                for yc in tickers:
                    sid,mkt=mkt_map[yc]
                    try:
                        df_p=raw[yc] if len(tickers)>1 else raw
                        if df_p is None or df_p.empty or "Close" not in df_p.columns: continue
                        df_p=df_p.dropna(subset=["Close"])
                        res=calc_signals(df_p,cross_bars,slope_bars,signal_types)
                        if res: res["代號"]=sid; res["市場"]=mkt; results2.append(res)
                    except: pass
                time.sleep(0.3)

            prog.progress(1.0,"✅ 掃描完成"); status.empty()

            if results2:
                rdf2=pd.DataFrame(results2)
                try:
                    nm_r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",
                                      timeout=10,headers=HEADERS,verify=False)
                    nm=pd.DataFrame(nm_r.json())[["公司代號","公司簡稱"]].copy()
                    nm.columns=["代號","名稱"]; nm["代號"]=nm["代號"].str.strip()
                    rdf2=rdf2.merge(nm,on="代號",how="left")
                    rdf2["名稱"]=rdf2.get("名稱",rdf2["代號"])
                except: rdf2["名稱"]=rdf2["代號"]

                col_order=["信號","市場","代號","名稱","收盤價",
                           "小橘240MA","小綠60MA","小藍20MA",
                           "vs小橘240MA","vs小綠60MA","張飛警示"]
                rdf2=rdf2[[c for c in col_order if c in rdf2.columns]]

                st.markdown(f"### ⚔️ 三刀流結果｜{datetime.now().strftime('%Y-%m-%d %H:%M')}")
                sig_order=["🔴 三刀做多","🟡 反彈做多","🟣 修正做空","🔵 三刀做空"]
                c1,c2,c3,c4=st.columns(4)
                for col,sig in zip([c1,c2,c3,c4],sig_order):
                    col.metric(sig, f"{len(rdf2[rdf2['信號']==sig])} 檔")

                # ── 🤖 AI 推薦 ────────────────────────────
                if show_ai and len(rdf2)>0:
                    st.markdown("---")
                    with st.spinner("🤖 AI 分析最佳標的..."):
                        rec=ai_recommend(rdf2," / ".join(signal_types))
                    if rec and "error" not in rec:
                        cf={"高":"🟢","中":"🟡","低":"🔴"}.get(rec.get("confidence","中"),"🟡")
                        rk={"高":"🔴","中":"🟡","低":"🟢"}.get(rec.get("risk","中"),"🟡")
                        st.markdown(f"""
<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border:2px solid #e94560;
border-radius:12px;padding:20px;margin:10px 0;">
<div style="display:flex;align-items:center;gap:12px;margin-bottom:12px;">
  <span style="font-size:2em;">🤖</span>
  <div>
    <div style="color:#e94560;font-size:0.85em;font-weight:600;letter-spacing:2px;">AI 專業推薦</div>
    <div style="color:white;font-size:1.6em;font-weight:700;">
      {rec.get('stock_id','')} {rec.get('name','')}
      <span style="background:#e94560;color:white;font-size:0.5em;padding:3px 8px;
      border-radius:4px;margin-left:8px;vertical-align:middle;">⭐ MARK</span>
    </div>
  </div>
</div>
<div style="color:#a8b2d8;margin-bottom:6px;"><strong style="color:#ccd6f6;">信號：</strong>{rec.get('signal','')}</div>
<div style="color:#a8b2d8;margin-bottom:6px;"><strong style="color:#ccd6f6;">推薦理由：</strong>{rec.get('reason','')}</div>
<div style="color:#a8b2d8;margin-bottom:12px;"><strong style="color:#ccd6f6;">操作重點：</strong>{rec.get('key_point','')}</div>
<div style="display:flex;gap:20px;">
  <span style="color:#a8b2d8;">信心度：{cf} <strong style="color:white;">{rec.get('confidence','')}</strong></span>
  <span style="color:#a8b2d8;">風險：{rk} <strong style="color:white;">{rec.get('risk','')}</strong></span>
</div>
<div style="margin-top:10px;color:#636e8a;font-size:0.75em;">⚠️ AI 推薦僅供參考，不構成投資建議，請自行判斷</div>
</div>""", unsafe_allow_html=True)
                    elif rec and "error" in rec:
                        st.warning(f"AI 暫時無法使用：{rec['error']}")

                st.markdown("---")
                for sig in sig_order:
                    sub=rdf2[rdf2["信號"]==sig]
                    if len(sub)>0:
                        st.markdown(f"#### {sig}（{len(sub)} 檔）")
                        st.dataframe(sub.drop(columns=["信號"]),use_container_width=True)

                csv2=rdf2.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("💾 下載結果 CSV",csv2,
                    f"三刀流_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    "text/csv",use_container_width=True)
                if err>0: st.caption(f"⚠️ {err} 批次失敗")
            else:
                st.info("目前無符合條件的股票，可調整穿越根數或信號類型後重試")
        else:
            st.markdown("""
**三刀流操作說明：**

| 均線 | 顏色 | 功能 |
|------|------|------|
| 240MA | 🟠 小橘（劉備） | 決定大方向 |
| 60MA  | 🟢 小綠（關羽） | 進出場節奏 |
| 20MA  | 🔵 小藍（張飛） | 出場控風險 |

**使用步驟：**
1. 選擇要掃描的信號類型
2. 設定穿越判斷 K 棒數（建議 2～3）
3. 開啟 🤖 AI 推薦
4. 按「⚔️ 開始三刀掃描」（全市場約 3～8 分鐘）
            """)
