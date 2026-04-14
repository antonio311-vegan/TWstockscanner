# ============================================================
# 📊 台股掃描器 v8
# 改進：
# 1. 策略卡片可點擊進入個別詳情頁
# 2. 進入詳情直接顯示已掃描結果（不重新掃描）
# 3. 每個策略有獨立參數面板，可調整後重新掃描
# 4. 主頁 / 個別策略頁 導覽
# ============================================================

import streamlit as st
import pandas as pd
import numpy as np
import requests
import yfinance as yf
import time, json, warnings
from datetime import datetime, timedelta
import pytz

warnings.filterwarnings("ignore")
requests.packages.urllib3.disable_warnings()

HEADERS = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0",
    "Accept":"application/json, text/javascript, */*; q=0.01",
    "Accept-Language":"zh-TW,zh;q=0.9",
    "Referer":"https://www.tpex.org.tw/",
}
TW_TZ = pytz.timezone("Asia/Taipei")

st.set_page_config(page_title="台股掃描器", page_icon="📊", layout="wide",
                   initial_sidebar_state="collapsed")

# ════════════════════════════════════════════════════════════
# CSS
# ════════════════════════════════════════════════════════════
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --bg:#ffffff; --bg2:#f8f9fc; --bg3:#f0f2f7;
  --border:#e2e6ef; --text:#1a2035; --dim:#7a8499;
  --c1:#0070f3; --c1-bg:#eff6ff; --c1-light:#dbeafe;
  --c2:#f97316; --c2-bg:#fff7ed; --c2-light:#fed7aa;
  --c3:#16a34a; --c3-bg:#f0fdf4; --c3-light:#bbf7d0;
  --danger:#dc2626; --warn:#d97706;
  --shadow:0 2px 12px rgba(0,0,0,0.08);
  --shadow-md:0 4px 20px rgba(0,0,0,0.12);
}

html,body,[data-testid="stAppViewContainer"]{background:var(--bg)!important;color:var(--text)!important;font-family:'Noto Sans TC',sans-serif!important;}
[data-testid="stHeader"]{background:white!important;border-bottom:1px solid var(--border);}
#MainMenu,footer,[data-testid="stToolbar"]{display:none!important;}
[data-testid="stSidebar"]{display:none!important;}
.block-container{padding:0!important;max-width:100%!important;}

.stButton>button{background:white!important;border:1.5px solid var(--border)!important;color:var(--text)!important;font-family:'Noto Sans TC',sans-serif!important;border-radius:8px!important;transition:all 0.18s!important;}
.stButton>button:hover{border-color:var(--c1)!important;color:var(--c1)!important;background:var(--c1-bg)!important;}
[data-testid="stExpander"]{background:white!important;border:1px solid var(--border)!important;border-radius:10px!important;box-shadow:var(--shadow)!important;}
.stTabs [data-baseweb="tab-list"]{background:var(--bg2)!important;border-radius:8px!important;}
.stTabs [aria-selected="true"]{color:var(--text)!important;font-weight:600!important;}

/* ── 頂部欄 ── */
.topbar{background:white;border-bottom:1px solid var(--border);padding:10px 24px;display:flex;align-items:center;justify-content:space-between;position:sticky;top:0;z-index:100;}
.topbar-brand{display:flex;align-items:center;gap:10px;}
.topbar-icon{width:30px;height:30px;background:var(--c1);border-radius:7px;display:flex;align-items:center;justify-content:center;color:white;font-size:1em;}
.topbar-title{font-size:0.95em;font-weight:700;}
.topbar-time{font-family:'JetBrains Mono',monospace;font-size:0.8em;color:var(--dim);}
.mkt-badge{padding:3px 10px;border-radius:20px;font-size:0.78em;font-weight:600;}
.mkt-open{background:#dcfce7;color:#16a34a;}
.mkt-closed{background:var(--bg3);color:var(--dim);}

/* ── 麵包屑 ── */
.breadcrumb{display:flex;align-items:center;gap:6px;font-size:0.82em;color:var(--dim);padding:10px 24px;background:var(--bg2);border-bottom:1px solid var(--border);}
.breadcrumb a{color:var(--c1);cursor:pointer;text-decoration:none;}
.breadcrumb a:hover{text-decoration:underline;}
.breadcrumb-sep{color:var(--border);}

/* ── 主內容包裝 ── */
.main-wrap{padding:20px 24px;}

/* ── 全部掃描按鈕 ── */
.scan-all-wrap{margin-bottom:20px;}

/* ── 策略卡片（可點擊）── */
.s-card{background:white;border:1px solid var(--border);border-radius:12px;padding:0;box-shadow:var(--shadow);border-top:4px solid;cursor:pointer;transition:all 0.2s;overflow:hidden;}
.s-card:hover{box-shadow:var(--shadow-md);transform:translateY(-2px);}
.s-card.c1{border-top-color:var(--c1);}
.s-card.c2{border-top-color:var(--c2);}
.s-card.c3{border-top-color:var(--c3);}
.s-card-body{padding:18px 20px 14px;}
.s-tag{font-size:0.67em;font-weight:700;letter-spacing:2px;color:var(--dim);margin-bottom:5px;}
.s-name{font-size:1.05em;font-weight:700;margin-bottom:3px;}
.c1 .s-name{color:var(--c1);}
.c2 .s-name{color:var(--c2);}
.c3 .s-name{color:var(--c3);}
.s-desc{font-size:0.78em;color:var(--dim);margin-bottom:12px;}
.scan-status{display:flex;align-items:center;gap:5px;font-size:0.73em;color:var(--dim);margin-bottom:8px;}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;}
.dot-green{background:var(--c3);}
.dot-grey{background:#ccc;}
.s-stats{display:flex;border-top:1px solid var(--border);padding:12px 20px;}
.s-stat{flex:1;text-align:center;}
.s-stat+.s-stat{border-left:1px solid var(--border);}
.s-num{font-family:'JetBrains Mono',monospace;font-size:1.7em;font-weight:700;}
.c1 .s-num{color:var(--c1);}
.c2 .s-num{color:var(--c2);}
.c3 .s-num{color:var(--c3);}
.s-lbl{font-size:0.68em;color:var(--dim);margin-top:2px;}
.s-footer{padding:8px 20px;background:var(--bg2);border-top:1px solid var(--border);font-size:0.75em;color:var(--c1);font-weight:500;}

/* ── 快訊列 ── */
.alert-row{display:flex;align-items:center;gap:8px;padding:6px 10px;border-radius:6px;margin:3px 0;background:var(--bg2);font-size:0.82em;border-left:3px solid transparent;}
.alert-row.c1{border-left-color:var(--c1);}
.alert-row.c2{border-left-color:var(--c2);}
.alert-row.c3{border-left-color:var(--c3);}
.alert-row.cdanger{border-left-color:var(--danger);}
.a-code{font-family:'JetBrains Mono',monospace;font-weight:700;color:var(--text);min-width:40px;}
.a-name{color:var(--dim);flex:1;}
.text-c1{color:var(--c1);}
.text-c2{color:var(--c2);}
.text-c3{color:var(--c3);}
.text-up{color:var(--danger);}
.text-down{color:var(--c3);}
.text-warn{color:var(--warn);}
.text-dim{color:var(--dim);}
.a-val{font-family:'JetBrains Mono',monospace;margin-left:auto;}

/* ── 詳情頁 ── */
.detail-hero{background:white;border:1px solid var(--border);border-radius:12px;padding:20px 24px;margin-bottom:18px;border-left:5px solid;}
.detail-hero.c1{border-left-color:var(--c1);}
.detail-hero.c2{border-left-color:var(--c2);}
.detail-hero.c3{border-left-color:var(--c3);}
.detail-title{font-size:1.3em;font-weight:700;margin-bottom:4px;}
.detail-meta{font-size:0.8em;color:var(--dim);}

/* ── 參數面板 ── */
.param-panel{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:16px 18px;margin-bottom:16px;}
.param-title{font-size:0.78em;font-weight:700;letter-spacing:1px;color:var(--dim);margin-bottom:12px;display:flex;align-items:center;gap:6px;}
.param-row{display:flex;align-items:center;justify-content:space-between;padding:5px 0;border-bottom:1px solid var(--border);font-size:0.83em;}
.param-row:last-child{border-bottom:none;}
.param-key{color:var(--dim);}
.param-val{font-family:'JetBrains Mono',monospace;font-weight:600;color:var(--text);}

/* ── AI 推薦卡 ── */
.ai-card{background:var(--bg2);border:1px solid var(--border);border-radius:10px;padding:16px;margin-bottom:14px;}
.ai-tag{font-size:0.68em;font-weight:700;letter-spacing:2px;color:var(--dim);margin-bottom:8px;}
.ai-name{font-size:1.1em;font-weight:700;color:var(--text);margin-bottom:4px;}
.ai-mark{background:var(--c1);color:white;font-size:0.55em;padding:2px 6px;border-radius:3px;margin-left:6px;vertical-align:middle;}
.ai-row{font-size:0.82em;color:var(--dim);margin:3px 0;}
.ai-row strong{color:var(--text);}
.ai-badges{display:flex;gap:8px;margin-top:8px;}
.badge{padding:3px 9px;border-radius:5px;font-size:0.76em;font-weight:600;}
.badge-high{background:#dcfce7;color:#16a34a;}
.badge-mid{background:#fef9c3;color:#854d0e;}
.badge-low{background:#fee2e2;color:#991b1b;}
.ai-disc{font-size:0.68em;color:#aaa;margin-top:8px;}

/* ── 分隔 ── */
.divider{border:none;border-top:1px solid var(--border);margin:16px 0;}

/* ── 漲停警報 ── */
@keyframes lflash{0%,100%{background:#fee2e2}50%{background:#fecaca}}
.limit-banner{animation:lflash 1.5s infinite;border:1.5px solid var(--danger);border-radius:10px;padding:10px 16px;margin:12px 0;display:flex;align-items:center;gap:10px;}
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# Session State
# ════════════════════════════════════════════════════════════
DEFAULTS = {
    "page": "home",          # home | force | sword | limit
    # 掃描結果
    "force_result": None, "force_latest": None, "force_time": "—",
    "sword_result": None, "sword_time": "—",
    "limit_result": None, "limit_time": "—",
    # 主力訊號參數
    "p_t1": 1.0, "p_t2": 2.5, "p_tm": 3.0, "p_vm": 2.0, "p_vx": 5.0,
    # 三刀流參數
    "p_cb": 2, "p_sb": 3,
    "p_sigs": ["🔴 三刀做多","🟡 反彈做多"],
    # 漲停獵手參數
    "p_lt1": 1.0, "p_lt2": 2.5, "p_ltm": 3.0, "p_min_score": 25,
}
for k, v in DEFAULTS.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ════════════════════════════════════════════════════════════
# 工具函數
# ════════════════════════════════════════════════════════════
def clean_num(s):
    if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
    return pd.to_numeric(pd.Series(s).astype(str).str.replace(",","").str.replace(" ","").str.strip(), errors="coerce")

def get_weekdays(n=30):
    dates, d = [], datetime.today()
    for _ in range(n):
        if d.weekday() < 5: dates.append(d.strftime("%Y%m%d"))
        d -= timedelta(days=1)
    return dates

def is_trading():
    now = datetime.now(TW_TZ)
    if now.weekday() >= 5: return False
    t = now.time()
    return datetime.strptime("09:00","%H:%M").time() <= t <= datetime.strptime("13:30","%H:%M").time()

def tw_now(): return datetime.now(TW_TZ)
def tw_now_str(): return datetime.now(TW_TZ).strftime("%H:%M:%S")
def weekday_zh(): return ["一","二","三","四","五","六","日"][tw_now().weekday()]

def go(page): st.session_state.page = page; st.rerun()

# ════════════════════════════════════════════════════════════
# 資料層
# ════════════════════════════════════════════════════════════
@st.cache_data(ttl=1800)
def get_main_data():
    NEED=8; wdays=get_weekdays()
    r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",timeout=15,headers=HEADERS,verify=False)
    raw=pd.DataFrame(r.json()); col=[c for c in raw.columns if "發行" in c and "股" in c][0]
    sh=raw[["公司代號",col]].copy(); sh.columns=["stock_id","shares"]
    sh["stock_id"]=sh["stock_id"].str.strip(); sh["shares"]=clean_num(sh["shares"])
    sh=sh.dropna().query("shares>0").reset_index(drop=True)
    twse_f=[]
    for d in wdays:
        url=f"https://www.twse.com.tw/exchangeReport/STOCK_DAY_ALL?response=json&date={d}"
        try:
            resp=requests.get(url,timeout=15,headers=HEADERS,verify=False); data=resp.json()
            if data.get("stat")=="OK" and len(data.get("data",[]))>50:
                df=pd.DataFrame(data["data"],columns=data["fields"]); df["date"]=pd.to_datetime(d,format="%Y%m%d"); twse_f.append(df)
        except: pass
        if len(twse_f)>=NEED: break
        time.sleep(0.4)
    if not twse_f: raise ValueError("TWSE_EMPTY")
    twse=pd.concat(twse_f,ignore_index=True)
    twse=twse.rename(columns={"證券代號":"stock_id","證券名稱":"stock_name","成交股數":"vol_str","開盤價":"open_str","收盤價":"close_str"})
    twse["stock_id"]=twse["stock_id"].str.strip()
    twse["volume"]=clean_num(twse["vol_str"]); twse["open"]=clean_num(twse["open_str"])
    twse["close"]=clean_num(twse["close_str"]); twse["market"]="上市"
    twse=twse.merge(sh,on="stock_id",how="inner").dropna(subset=["volume","shares","open","close"])
    twse=twse.query("volume>0 and shares>0 and close>0").copy()
    twse["turnover_rate"]=twse["volume"]/twse["shares"]*100
    TPEX_COLS=["stock_id","stock_name","close_str","change","open_str","high","low","vol_str","amount","trades","bid_p","bid_v","ask_p","ask_v","shares_str","limit_up","limit_down"]
    tpex_f=[]
    for d in wdays:
        dt=datetime.strptime(d,"%Y%m%d"); roc=f"{dt.year-1911}/{dt.month:02d}/{dt.day:02d}"
        for url in [f"https://www.tpex.org.tw/web/stock/aftertrading/all_daily_info/mpsas_result.php?l=zh-tw&o=json&d={roc}&s=0,asc",
                    f"https://openapi.tpex.org.tw/v1/tpex_mainboard_daily_close_quotes?date={roc}&charset=UTF-8"]:
            try:
                sess=requests.Session(); sess.headers.update(HEADERS)
                try: sess.get("https://www.tpex.org.tw/",timeout=5,verify=False)
                except: pass
                resp=sess.get(url,timeout=12,verify=False); raw2=resp.text.strip()
                if not raw2 or raw2[0] not in "[{": continue
                data=resp.json(); rows=data.get("aaData") or (data if isinstance(data,list) else [])
                if len(rows)>50:
                    if isinstance(rows[0],list):
                        n=len(rows[0]); df=pd.DataFrame(rows,columns=TPEX_COLS[:n])
                        df["volume"]=clean_num(df["vol_str"]); df["shares"]=clean_num(df["shares_str"])
                        df["open"]=clean_num(df["open_str"]); df["close"]=clean_num(df["close_str"])
                    else:
                        df=pd.DataFrame(rows); df=df.loc[:,~df.columns.duplicated()]
                        FM={"SecuritiesCompanyCode":"stock_id","CompanyName":"stock_name","Close":"close","Open":"open","TradeVolume":"volume","IssuedShares":"shares"}
                        df=df.rename(columns={k:v for k,v in FM.items() if k in df.columns})
                        for c in ["volume","shares","open","close"]:
                            if c in df.columns: df[c]=clean_num(df[c])
                        if "stock_name" not in df.columns: df["stock_name"]=df.get("stock_id","")
                    df["date"]=pd.to_datetime(d,format="%Y%m%d"); df["market"]="上櫃"
                    df["stock_id"]=df["stock_id"].astype(str).str.strip(); tpex_f.append(df); break
            except: pass
        if len(tpex_f)>=NEED: break
        time.sleep(0.5)
    KEEP=["stock_id","stock_name","date","open","close","volume","shares","turnover_rate","market"]
    if tpex_f:
        tpex_all=pd.concat(tpex_f,ignore_index=True).dropna(subset=["volume","shares","open","close"])
        tpex_all=tpex_all.query("volume>0 and shares>0 and close>0").copy()
        tpex_all["turnover_rate"]=tpex_all["volume"]/tpex_all["shares"]*100
        df_all=pd.concat([twse[KEEP],tpex_all[KEEP]],ignore_index=True)
    else: df_all=twse[KEEP].copy()
    return df_all.sort_values(["stock_id","date"]).reset_index(drop=True)

def do_scan_force(df, t1,t2,tm,vm,vx):
    latest=df["date"].max(); results=[]
    for sid,grp in df.groupby("stock_id"):
        grp=grp.sort_values("date"); tr=grp[grp["date"]==latest]
        if tr.empty: continue
        p5=grp[grp["date"]<latest].tail(5)
        if len(p5)<5: continue
        row=tr.iloc[0]; t_now=row["turnover_rate"]; t_avg=p5["turnover_rate"].mean()
        v_now=row["volume"]; v_avg=p5["volume"].mean()
        if t_avg<=0 or v_avg<=0: continue
        tr_=t_now/t_avg; vr_=v_now/v_avg
        if t_avg<t1 and t_now>=t2 and tr_>=tm and vm<=vr_<=vx:
            chg=round(((row["close"]-row["open"])/row["open"])*100,2) if row["open"]>0 else 0
            results.append({"代號":sid,"名稱":row.get("stock_name",""),"收盤":row["close"],
                "漲跌(%)":chg,"五日均週轉(%)":round(t_avg,3),"今日週轉(%)":round(t_now,3),
                "週轉倍數":round(tr_,1),"量比":round(vr_,1),"市場":row.get("market","")})
    rdf=pd.DataFrame(results)
    if not rdf.empty: rdf=rdf.sort_values("週轉倍數",ascending=False).reset_index(drop=True)
    return rdf, latest

def calc_three_sword(df_p, cross_n, slope_n, sig_types):
    if len(df_p)<260: return None
    c=df_p["Close"].values
    ma20=pd.Series(c).rolling(20).mean().values
    ma60=pd.Series(c).rolling(60).mean().values
    ma240=pd.Series(c).rolling(240).mean().values
    price=c[-1]; m20=ma20[-1]; m60=ma60[-1]; m240=ma240[-1]
    if any(np.isnan(v) for v in [m20,m60,m240]): return None
    slope_20=m20-ma20[-(slope_n+1)] if len(ma20)>slope_n else 0
    pos_s=slope_20>0; neg_s=slope_20<0
    def cup(f,s,n):
        for i in range(1,n+1):
            if -(i+1)<-len(f): break
            if f[-(i+1)]<s[-(i+1)] and f[-i]>=s[-i]: return True
        return False
    def cdn(f,s,n):
        for i in range(1,n+1):
            if -(i+1)<-len(f): break
            if f[-(i+1)]>s[-(i+1)] and f[-i]<=s[-i]: return True
        return False
    ab240=price>m240; ab60=price>m60
    ja60=cup(c,ma60,cross_n); jb60=cdn(c,ma60,cross_n)
    signal=None
    if "🔴 三刀做多" in sig_types and ab240 and ab60 and ja60: signal="🔴 三刀做多"
    if not signal and "🟡 反彈做多" in sig_types and not ab240 and ja60: signal="🟡 反彈做多"
    if not signal and "🟣 修正做空" in sig_types and ab240 and jb60: signal="🟣 修正做空"
    if not signal and "🔵 三刀做空" in sig_types and not ab240 and not ab60 and jb60: signal="🔵 三刀做空"
    if not signal: return None
    zw=("⚠️ 注意下車" if neg_s else "✅ 多頭有力") if signal in ["🔴 三刀做多","🟡 反彈做多"] else ("⚠️ 注意平倉" if pos_s else "✅ 空頭有力")
    return {"信號":signal,"收盤":round(price,2),"240MA":round(m240,2),"60MA":round(m60,2),
            "20MA":round(m20,2),"vs240MA":"✅" if ab240 else "❌","vs60MA":"✅" if ab60 else "❌","張飛":zw}

def do_scan_sword(cross_n, slope_n, sig_types):
    try:
        r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",timeout=15,headers=HEADERS,verify=False)
        sid_list=[s.strip() for s in pd.DataFrame(r.json())["公司代號"].tolist() if s.strip().isdigit()][:250]
    except: sid_list=[]
    results2=[]; total=len(sid_list); BATCH=25
    prog=st.progress(0,"⚔️ 掃描中...")
    for bs in range(0,total,BATCH):
        batch=sid_list[bs:bs+BATCH]; tickers=[s+".TW" for s in batch]
        prog.progress(int(bs/total*100)/100, f"⚔️ {bs}/{total}...")
        try:
            raw=yf.download(tickers,period="60d",interval="60m",group_by="ticker",auto_adjust=True,progress=False,threads=True)
        except: continue
        for yc in tickers:
            sid=yc.split(".")[0]
            try:
                df_p=raw[yc] if len(tickers)>1 else raw
                if df_p is None or df_p.empty or "Close" not in df_p.columns: continue
                res=calc_three_sword(df_p.dropna(subset=["Close"]),cross_n,slope_n,sig_types)
                if res: res["代號"]=sid; res["市場"]="上市"; results2.append(res)
            except: pass
        time.sleep(0.3)
    prog.empty()
    if results2:
        rdf2=pd.DataFrame(results2)
        nm=get_name_map(); rdf2["名稱"]=rdf2["代號"].map(nm).fillna("")
        col_order=["信號","市場","代號","名稱","收盤","240MA","60MA","20MA","vs240MA","vs60MA","張飛"]
        return rdf2[[c for c in col_order if c in rdf2.columns]]
    return pd.DataFrame()

def do_scan_limit(df, t1,t2,tm,min_score):
    rdf_force,_=do_scan_force(df,t1,t2,tm,1.5,6.0)
    force_ids=set(rdf_force["代號"].tolist()) if not rdf_force.empty else set()
    latest=df["date"].max(); today=df[df["date"]==latest].copy()
    prev_day=df[df["date"]<latest].groupby("stock_id").last()
    nm=get_name_map(); scores=[]
    for sid, row in today.set_index("stock_id").iterrows():
        prev=prev_day.loc[sid] if sid in prev_day.index else None
        chg=round((row["close"]-prev["close"])/prev["close"]*100,2) if prev is not None and prev["close"]>0 else 0
        recent=df[df["stock_id"]==sid].tail(6)
        high5=recent["close"].iloc[:-1].max() if len(recent)>1 else 0
        closes=df[df["stock_id"]==sid].tail(10)["close"].values
        bull_ma=(len(closes)>=10 and closes[-1]>closes[-5:].mean()>closes.mean())
        score=0; flags=[]
        if sid in force_ids: score+=30; flags.append("📈主力")
        if 7<=chg<9.5: score+=20; flags.append(f"🔥{chg:.1f}%")
        elif 5<=chg<7: score+=10; flags.append(f"📊{chg:.1f}%")
        if row["close"]>high5: score+=15; flags.append("🎯高點")
        if bull_ma: score+=10; flags.append("📐多頭")
        if score>=min_score:
            scores.append({"評分":min(score,100),"代號":sid,"名稱":nm.get(sid,""),
                "昨收":row["close"],"漲停價":round(row["close"]*1.1,1),
                "已漲停":"","觸發條件":" | ".join(flags)})
    lr=pd.DataFrame(scores).sort_values("評分",ascending=False).reset_index(drop=True) if scores else pd.DataFrame()
    return lr

@st.cache_data(ttl=86400)
def get_name_map():
    try:
        r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",timeout=10,headers=HEADERS,verify=False)
        nm=pd.DataFrame(r.json())[["公司代號","公司簡稱"]]; nm.columns=["代號","名稱"]
        nm["代號"]=nm["代號"].str.strip(); return dict(zip(nm["代號"],nm["名稱"]))
    except: return {}

def ai_recommend(df_r, scan_type):
    if df_r is None or df_r.empty: return None
    rows_str=df_r.head(12).to_string(index=False)
    prompt=f"""你是台股專業投資人，20年經驗。掃描信號：{scan_type}
清單：\n{rows_str}
選最值得關注的一檔。只回覆JSON不加其他：
{{"stock_id":"代號","name":"名稱","signal":"信號","reason":"理由40字內繁體中文","key_point":"操作重點20字內","confidence":"高/中/低","risk":"高/中/低"}}"""
    try:
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":280,
                  "messages":[{"role":"user","content":prompt}]},timeout=25)
        text=resp.json()["content"][0]["text"].strip()
        return json.loads(text.replace("```json","").replace("```","").strip())
    except Exception as e: return {"error":str(e)}

def show_ai_card(rec, color="var(--c1)"):
    if not rec or "error" in rec: return
    cf={"高":"badge-high","中":"badge-mid","低":"badge-low"}.get(rec.get("confidence","中"),"badge-mid")
    rk={"高":"badge-low","中":"badge-mid","低":"badge-high"}.get(rec.get("risk","中"),"badge-mid")
    st.markdown(f"""
<div class="ai-card">
  <div class="ai-tag">🤖 AI RECOMMENDATION</div>
  <div class="ai-name">{rec.get('stock_id','')} {rec.get('name','')}
    <span class="ai-mark">⭐ MARK</span></div>
  <div class="ai-row"><strong>信號：</strong>{rec.get('signal','')}</div>
  <div class="ai-row"><strong>理由：</strong>{rec.get('reason','')}</div>
  <div class="ai-row"><strong>操作：</strong>{rec.get('key_point','')}</div>
  <div class="ai-badges">
    <span class="badge {cf}">信心：{rec.get('confidence','')}</span>
    <span class="badge {rk}">風險：{rec.get('risk','')}</span>
  </div>
  <div class="ai-disc">⚠️ 僅供參考，不構成投資建議</div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 頂部欄（每頁共用）
# ════════════════════════════════════════════════════════════
mkt_open=is_trading(); now_tw=tw_now()

st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">
    <div class="topbar-icon">📊</div>
    <div>
      <div class="topbar-title">台股掃描器</div>
    </div>
  </div>
  <div class="topbar-time">{now_tw.strftime('%Y-%m-%d %H:%M:%S')}　星期{weekday_zh()}</div>
  <span class="mkt-badge {'mkt-open' if mkt_open else 'mkt-closed'}">{'● 交易中' if mkt_open else '● 休市'}</span>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 頁面路由
# ════════════════════════════════════════════════════════════
page = st.session_state.page

# ════════════════════════════════════════════════════════════
# 🏠 首頁
# ════════════════════════════════════════════════════════════
if page == "home":

    # 麵包屑
    st.markdown('<div class="breadcrumb">🏠 首頁</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

    # 全部掃描按鈕
    b1,b2,b3,b4 = st.columns([2,1,1,1])
    with b1:
        scan_all = st.button("🚀 全部掃描（三策略同步）", type="primary", use_container_width=True, key="home_scan_all")
    with b2:
        if st.button("🗑️ 清除快取", use_container_width=True, key="home_clr"):
            st.cache_data.clear(); st.toast("快取已清除"); st.rerun()
    with b3:
        pass
    with b4:
        pass

    # 三策略卡片
    st.markdown('<div style="height:14px;"></div>', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3, gap="medium")

    fr    = st.session_state.force_result
    sr    = st.session_state.sword_result
    lr    = st.session_state.limit_result
    f_cnt = (len(fr) if fr is not None and not isinstance(fr,type(None)) and hasattr(fr,'__len__') and len(fr)>0 else 0)
    s_cnt = (len(sr) if sr is not None and not isinstance(sr,type(None)) and hasattr(sr,'__len__') and len(sr)>0 else 0)
    l_cnt = (len(lr) if lr is not None and not isinstance(lr,type(None)) and hasattr(lr,'__len__') and len(lr)>0 else 0)
    sc    = sr["信號"].value_counts().to_dict() if sr is not None and s_cnt>0 else {}
    lim70 = (len(lr[lr["評分"]>=70]) if lr is not None and l_cnt>0 else 0)

    with col1:
        st.markdown(f"""
<div class="s-card c1">
  <div class="s-card-body">
    <div class="s-tag">STRATEGY 01</div>
    <div class="s-name">🎯 主力進場訊號</div>
    <div class="s-desc">沉寂股突然爆量，主力可能進場布局</div>
    <div class="scan-status"><span class="dot {'dot-green' if f_cnt>0 else 'dot-grey'}"></span>最後掃描：{st.session_state.force_time}</div>
  </div>
  <div class="s-stats">
    <div class="s-stat"><div class="s-num c1">{f_cnt}</div><div class="s-lbl">符合股票</div></div>
    <div class="s-stat"><div class="s-num" style="color:{'var(--danger)' if f_cnt>0 else 'var(--dim)'};">{'🔴 活躍' if f_cnt>0 else '⚫ 無'}</div><div class="s-lbl">狀態</div></div>
  </div>
  <div class="s-footer">點擊進入 →</div>
</div>""", unsafe_allow_html=True)
        if st.button("進入主力訊號", key="go_force", use_container_width=True):
            go("force")

        # 快訊預覽
        if fr is not None and f_cnt>0:
            for _, row in fr.head(3).iterrows():
                chg=float(row.get("漲跌(%)","0") or 0)
                st.markdown(f"""<div class="alert-row c1">
  <span class="a-code">{row['代號']}</span>
  <span class="a-name">{str(row.get('名稱',''))[:5]}</span>
  <span class="text-c1">{row['今日週轉(%)']}%</span>
  <span class="a-val text-warn">{row['週轉倍數']}x</span>
  <span class="a-val {'text-up' if chg>0 else 'text-down'}">{'+' if chg>0 else ''}{chg:.1f}%</span>
</div>""", unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
<div class="s-card c2">
  <div class="s-card-body">
    <div class="s-tag">STRATEGY 02</div>
    <div class="s-name">⚔️ 三刀流（60分K）</div>
    <div class="s-desc">🟠240MA　🟢60MA　🔵20MA</div>
    <div class="scan-status"><span class="dot {'dot-green' if s_cnt>0 else 'dot-grey'}"></span>最後掃描：{st.session_state.sword_time}</div>
  </div>
  <div class="s-stats">
    <div class="s-stat"><div class="s-num c2">{sc.get('🔴 三刀做多',0)}</div><div class="s-lbl">三刀做多</div></div>
    <div class="s-stat"><div class="s-num" style="color:var(--warn);">{sc.get('🟡 反彈做多',0)}</div><div class="s-lbl">反彈做多</div></div>
    <div class="s-stat"><div class="s-num c2">{s_cnt}</div><div class="s-lbl">合計</div></div>
  </div>
  <div class="s-footer">點擊進入 →</div>
</div>""", unsafe_allow_html=True)
        if st.button("進入三刀流", key="go_sword", use_container_width=True):
            go("sword")

        if sr is not None and s_cnt>0:
            sig_c={"🔴 三刀做多":"cdanger","🟡 反彈做多":"c2","🟣 修正做空":"c1","🔵 三刀做空":"c1"}
            for _, row in sr.head(3).iterrows():
                sc2=sig_c.get(row.get("信號",""),"c2")
                st.markdown(f"""<div class="alert-row {sc2}">
  <span class="a-code">{row['代號']}</span>
  <span class="a-name">{str(row.get('名稱',''))[:5]}</span>
  <span class="text-c2" style="font-size:0.9em;">{row.get('信號','')}</span>
</div>""", unsafe_allow_html=True)

    with col3:
        st.markdown(f"""
<div class="s-card c3">
  <div class="s-card-body">
    <div class="s-tag">STRATEGY 03</div>
    <div class="s-name">🎯 漲停獵手</div>
    <div class="s-desc">綜合評分預測漲停潛力股</div>
    <div class="scan-status"><span class="dot {'dot-green' if l_cnt>0 else 'dot-grey'}"></span>最後掃描：{st.session_state.limit_time}</div>
  </div>
  <div class="s-stats">
    <div class="s-stat"><div class="s-num c3">{lim70}</div><div class="s-lbl">高分70+</div></div>
    <div class="s-stat"><div class="s-num c3">{l_cnt}</div><div class="s-lbl">候選總數</div></div>
  </div>
  <div class="s-footer">點擊進入 →</div>
</div>""", unsafe_allow_html=True)
        if st.button("進入漲停獵手", key="go_limit", use_container_width=True):
            go("limit")

        if lr is not None and l_cnt>0:
            for _, row in lr.head(3).iterrows():
                sc3=row.get("評分",0)
                st.markdown(f"""<div class="alert-row c3">
  <span class="a-code">{row['代號']}</span>
  <span class="a-name">{str(row.get('名稱',''))[:5]}</span>
  <span class="badge {'badge-low' if sc3>=70 else 'badge-high'}" style="font-size:0.75em;">{sc3}分</span>
  <span class="a-val text-dim" style="font-size:0.78em;">{str(row.get('觸發條件',''))[:15]}</span>
</div>""", unsafe_allow_html=True)

    # 全部掃描執行
    if scan_all:
        st.markdown('<hr class="divider">', unsafe_allow_html=True)
        st.markdown("### 🚀 三策略同步掃描中...")
        p1,p2,p3=st.columns(3)
        with st.spinner("📡 載入歷史資料..."):
            try: df_hist=get_main_data()
            except Exception as e: st.error(f"❌ {e}"); df_hist=None

        if df_hist is not None:
            with st.spinner("🎯 主力訊號掃描..."):
                rdf,latest=do_scan_force(df_hist,st.session_state.p_t1,st.session_state.p_t2,st.session_state.p_tm,st.session_state.p_vm,st.session_state.p_vx)
                st.session_state.force_result=rdf; st.session_state.force_latest=latest; st.session_state.force_time=tw_now_str()
            with p1: st.success(f"✅ 主力訊號　{len(rdf)} 檔")

            st.markdown("**⚔️ 三刀流掃描中（約3～5分鐘）...**")
            sword_res=do_scan_sword(st.session_state.p_cb,st.session_state.p_sb,st.session_state.p_sigs)
            st.session_state.sword_result=sword_res; st.session_state.sword_time=tw_now_str()
            with p2: st.success(f"✅ 三刀流　{len(sword_res)} 檔")

            with st.spinner("🎯 漲停獵手掃描..."):
                lim_res=do_scan_limit(df_hist,st.session_state.p_lt1,st.session_state.p_lt2,st.session_state.p_ltm,st.session_state.p_min_score)
                st.session_state.limit_result=lim_res; st.session_state.limit_time=tw_now_str()
            with p3: st.success(f"✅ 漲停獵手　{len(lim_res)} 檔")
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 🎯 主力訊號詳情頁
# ════════════════════════════════════════════════════════════
elif page == "force":
    st.markdown("""
<div class="breadcrumb">
  <a onclick="void(0)" id="bc_home">🏠 首頁</a>
  <span class="breadcrumb-sep">›</span>
  <span>🎯 主力進場訊號</span>
</div>""", unsafe_allow_html=True)
    if st.button("← 返回首頁", key="force_back"): go("home")

    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

    # 詳情頁標題
    fr=st.session_state.force_result
    f_cnt=len(fr) if fr is not None and not fr.empty else 0
    st.markdown(f"""
<div class="detail-hero c1">
  <div class="detail-title">🎯 主力進場訊號</div>
  <div class="detail-meta">最後掃描：{st.session_state.force_time}　｜　符合股票：{f_cnt} 檔</div>
</div>""", unsafe_allow_html=True)

    # 兩欄：左邊參數，右邊結果
    param_col, result_col = st.columns([1, 2], gap="medium")

    with param_col:
        st.markdown("""<div class="param-panel">
  <div class="param-title">⚙️ 掃描參數</div>
</div>""", unsafe_allow_html=True)

        st.session_state.p_t1 = st.slider("訊號一：五日均週轉上限(%)", 0.5, 2.0, st.session_state.p_t1, 0.1, key="fp_t1")
        st.session_state.p_t2 = st.slider("訊號二：今日週轉下限(%)",   1.5, 5.0, st.session_state.p_t2, 0.1, key="fp_t2")
        st.session_state.p_tm = st.slider("訊號二：週轉倍數下限",       2.0, 5.0, st.session_state.p_tm, 0.5, key="fp_tm")
        st.session_state.p_vm = st.slider("訊號三：量比下限",           1.0, 3.0, st.session_state.p_vm, 0.5, key="fp_vm")
        st.session_state.p_vx = st.slider("訊號三：量比上限",           3.0, 8.0, st.session_state.p_vx, 0.5, key="fp_vx")

        # 目前參數一覽
        st.markdown(f"""<div class="param-panel" style="margin-top:8px;">
  <div class="param-title">📋 目前參數</div>
  <div class="param-row"><span class="param-key">五日均週轉上限</span><span class="param-val">&lt; {st.session_state.p_t1}%</span></div>
  <div class="param-row"><span class="param-key">今日週轉下限</span><span class="param-val">≥ {st.session_state.p_t2}%</span></div>
  <div class="param-row"><span class="param-key">週轉倍數下限</span><span class="param-val">≥ {st.session_state.p_tm}x</span></div>
  <div class="param-row"><span class="param-key">量比範圍</span><span class="param-val">{st.session_state.p_vm}x ～ {st.session_state.p_vx}x</span></div>
</div>""", unsafe_allow_html=True)

        if st.button("🔍 套用參數重新掃描", type="primary", use_container_width=True, key="force_rescan"):
            with st.spinner("📡 載入資料..."):
                try: df_hist=get_main_data()
                except Exception as e: st.error(f"❌ {e}"); df_hist=None
            if df_hist is not None:
                with st.spinner("🎯 掃描中..."):
                    rdf,latest=do_scan_force(df_hist,st.session_state.p_t1,st.session_state.p_t2,st.session_state.p_tm,st.session_state.p_vm,st.session_state.p_vx)
                    st.session_state.force_result=rdf; st.session_state.force_latest=latest; st.session_state.force_time=tw_now_str()
                st.rerun()

    with result_col:
        if fr is not None and not fr.empty:
            # AI 推薦
            with st.expander("🤖 AI 推薦（展開查看）", expanded=False):
                with st.spinner("分析中..."): rec=ai_recommend(fr,"主力進場訊號")
                show_ai_card(rec)

            # 數據摘要
            c1,c2,c3,c4=st.columns(4)
            c1.metric("符合股票", f"{f_cnt} 檔")
            if not fr.empty:
                c2.metric("最高週轉倍數", f"{fr['週轉倍數'].max():.1f}x")
                c3.metric("平均量比", f"{fr['量比'].mean():.1f}x")
                c4.metric("最高漲幅", f"{fr['漲跌(%)'].max():.1f}%")

            # 完整表格
            st.markdown("**📋 完整掃描結果**")
            def cc(v):
                try: return f"color:{'#dc2626' if float(v)>0 else '#16a34a' if float(v)<0 else '#888'}"
                except: return ""
            st.dataframe(fr.style.applymap(cc,subset=["漲跌(%)"]), use_container_width=True, height=420)
            csv=fr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("💾 下載 CSV", csv,
                f"主力_{st.session_state.force_latest.strftime('%Y%m%d') if st.session_state.force_latest else 'data'}.csv",
                "text/csv", use_container_width=True)
        elif fr is not None and fr.empty:
            st.info("此交易日無符合條件的股票，可調整左側參數後重新掃描")
        else:
            st.warning("尚未掃描，請點擊「套用參數重新掃描」或回首頁使用「全部掃描」")

    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# ⚔️ 三刀流詳情頁
# ════════════════════════════════════════════════════════════
elif page == "sword":
    if st.button("← 返回首頁", key="sword_back"): go("home")
    st.markdown("""<div class="breadcrumb">
  <span>🏠 首頁</span><span class="breadcrumb-sep">›</span><span>⚔️ 三刀流</span>
</div>""", unsafe_allow_html=True)

    sr=st.session_state.sword_result
    s_cnt=len(sr) if sr is not None and not sr.empty else 0

    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown(f"""
<div class="detail-hero c2">
  <div class="detail-title">⚔️ 刀神均線三刀流（60分K）</div>
  <div class="detail-meta">最後掃描：{st.session_state.sword_time}　｜　符合股票：{s_cnt} 檔　｜　🟠240MA　🟢60MA　🔵20MA</div>
</div>""", unsafe_allow_html=True)

    param_col2, result_col2 = st.columns([1, 2], gap="medium")

    with param_col2:
        st.markdown("""<div class="param-panel"><div class="param-title">⚙️ 掃描參數</div></div>""", unsafe_allow_html=True)

        st.session_state.p_sigs = st.multiselect("監控信號",
            ["🔴 三刀做多","🟡 反彈做多","🟣 修正做空","🔵 三刀做空"],
            default=st.session_state.p_sigs, key="sp_sigs")
        st.session_state.p_cb = st.slider("穿越判斷K棒數", 1, 5, st.session_state.p_cb, key="sp_cb")
        st.session_state.p_sb = st.slider("20MA斜率回看K棒數", 2, 10, st.session_state.p_sb, key="sp_sb")

        st.markdown(f"""<div class="param-panel" style="margin-top:8px;">
  <div class="param-title">📋 目前參數</div>
  <div class="param-row"><span class="param-key">穿越K棒數</span><span class="param-val">{st.session_state.p_cb} 根</span></div>
  <div class="param-row"><span class="param-key">斜率回看K棒</span><span class="param-val">{st.session_state.p_sb} 根</span></div>
  <div class="param-row"><span class="param-key">監控信號數</span><span class="param-val">{len(st.session_state.p_sigs)} 種</span></div>
</div>""", unsafe_allow_html=True)

        st.caption("⚠️ 三刀流掃描約需 3～5 分鐘")
        if st.button("⚔️ 套用參數重新掃描", type="primary", use_container_width=True, key="sword_rescan"):
            with st.spinner("⚔️ 掃描三刀流（約3～5分鐘）..."):
                sword_res=do_scan_sword(st.session_state.p_cb,st.session_state.p_sb,st.session_state.p_sigs)
                st.session_state.sword_result=sword_res; st.session_state.sword_time=tw_now_str()
            st.rerun()

    with result_col2:
        if sr is not None and not sr.empty:
            with st.expander("🤖 AI 推薦", expanded=False):
                with st.spinner("分析中..."): rec2=ai_recommend(sr,"三刀流多頭信號")
                show_ai_card(rec2,"var(--c2)")

            sig_order=["🔴 三刀做多","🟡 反彈做多","🟣 修正做空","🔵 三刀做空"]
            active=[s for s in sig_order if not sr[sr["信號"]==s].empty]

            # 信號摘要
            cols=st.columns(len(active)) if active else st.columns(1)
            colors={"🔴 三刀做多":"#dc2626","🟡 反彈做多":"#f97316","🟣 修正做空":"#7c3aed","🔵 三刀做空":"#0070f3"}
            for col_,sig in zip(cols,active):
                with col_:
                    cnt_=len(sr[sr["信號"]==sig])
                    clr=colors.get(sig,"#888")
                    st.markdown(f'<div style="text-align:center;padding:10px;background:var(--bg2);border-radius:8px;border-top:3px solid {clr};"><div style="font-size:1.4em;font-weight:700;color:{clr};">{cnt_}</div><div style="font-size:0.75em;color:var(--dim);">{sig}</div></div>', unsafe_allow_html=True)

            # 分 Tab 顯示
            if active:
                tabs_=st.tabs([f"{s}（{len(sr[sr['信號']==s])}）" for s in active])
                for tab_,sig in zip(tabs_,active):
                    with tab_:
                        st.dataframe(sr[sr["信號"]==sig].drop(columns=["信號"]),use_container_width=True,height=320)
            csv2=sr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("💾 下載 CSV",csv2,f"三刀流_{datetime.now().strftime('%Y%m%d_%H%M')}.csv","text/csv",use_container_width=True)
        elif sr is not None and sr.empty:
            st.info("此次掃描無符合三刀流條件的股票，可調整參數後重新掃描")
        else:
            st.warning("尚未掃描，請點擊左側「套用參數重新掃描」")

    st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 🎯 漲停獵手詳情頁
# ════════════════════════════════════════════════════════════
elif page == "limit":
    if st.button("← 返回首頁", key="limit_back"): go("home")
    st.markdown("""<div class="breadcrumb">
  <span>🏠 首頁</span><span class="breadcrumb-sep">›</span><span>🎯 漲停獵手</span>
</div>""", unsafe_allow_html=True)

    lr=st.session_state.limit_result
    l_cnt=len(lr) if lr is not None and not lr.empty else 0
    lim70=(len(lr[lr["評分"]>=70]) if l_cnt>0 else 0)

    st.markdown('<div class="main-wrap">', unsafe_allow_html=True)
    st.markdown(f"""
<div class="detail-hero c3">
  <div class="detail-title">🎯 漲停獵手</div>
  <div class="detail-meta">最後掃描：{st.session_state.limit_time}　｜　高分70+ ：{lim70} 檔　｜　候選總數：{l_cnt} 檔</div>
</div>""", unsafe_allow_html=True)

    param_col3, result_col3 = st.columns([1, 2], gap="medium")

    with param_col3:
        st.markdown("""<div class="param-panel"><div class="param-title">⚙️ 評分參數</div></div>""", unsafe_allow_html=True)

        st.session_state.p_lt1 = st.slider("主力：五日均週轉上限(%)", 0.5, 2.0, st.session_state.p_lt1, 0.1, key="lp_t1")
        st.session_state.p_lt2 = st.slider("主力：今日週轉下限(%)",   1.5, 5.0, st.session_state.p_lt2, 0.1, key="lp_t2")
        st.session_state.p_ltm = st.slider("主力：週轉倍數下限",       2.0, 5.0, st.session_state.p_ltm, 0.5, key="lp_tm")
        st.session_state.p_min_score = st.slider("最低顯示評分",       10,  80,  st.session_state.p_min_score, 5, key="lp_ms")

        st.markdown(f"""<div class="param-panel" style="margin-top:8px;">
  <div class="param-title">📋 評分說明</div>
  <div class="param-row"><span class="param-key">主力進場訊號</span><span class="param-val">+30 分</span></div>
  <div class="param-row"><span class="param-key">昨日漲幅 7-9.5%</span><span class="param-val">+20 分</span></div>
  <div class="param-row"><span class="param-key">突破近期高點</span><span class="param-val">+15 分</span></div>
  <div class="param-row"><span class="param-key">均線多頭排列</span><span class="param-val">+10 分</span></div>
  <div class="param-row"><span class="param-key">最低顯示分數</span><span class="param-val">≥ {st.session_state.p_min_score} 分</span></div>
</div>""", unsafe_allow_html=True)

        if st.button("🎯 套用參數重新掃描", type="primary", use_container_width=True, key="limit_rescan"):
            with st.spinner("📡 載入資料..."):
                try: df_hist=get_main_data()
                except Exception as e: st.error(f"❌ {e}"); df_hist=None
            if df_hist is not None:
                with st.spinner("🎯 掃描中..."):
                    lim_res=do_scan_limit(df_hist,st.session_state.p_lt1,st.session_state.p_lt2,st.session_state.p_ltm,st.session_state.p_min_score)
                    st.session_state.limit_result=lim_res; st.session_state.limit_time=tw_now_str()
                st.rerun()

    with result_col3:
        if lr is not None and not lr.empty:
            with st.expander("🤖 AI 推薦", expanded=False):
                with st.spinner("分析中..."): rec3=ai_recommend(lr.head(12),"漲停潛力股")
                show_ai_card(rec3,"var(--c3)")

            # 評分摘要
            c1,c2,c3,c4=st.columns(4)
            c1.metric("候選總數", f"{l_cnt} 檔")
            c2.metric("高分 70+", f"{lim70} 檔")
            c3.metric("50-70 分", f"{len(lr[(lr['評分']>=50)&(lr['評分']<70)])} 檔")
            c4.metric("最高評分", f"{lr['評分'].max()} 分")

            # 分 Tab 顯示
            t70,t50,t30,tall=st.tabs(["🔥 70+分","⚡ 50-70分","📊 30-50分","📋 全部"])
            with t70:  st.dataframe(lr[lr["評分"]>=70],use_container_width=True,height=280)
            with t50:  st.dataframe(lr[(lr["評分"]>=50)&(lr["評分"]<70)],use_container_width=True,height=280)
            with t30:  st.dataframe(lr[(lr["評分"]>=30)&(lr["評分"]<50)],use_container_width=True,height=280)
            with tall: st.dataframe(lr,use_container_width=True,height=280)

            csv3=lr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("💾 下載 CSV",csv3,f"漲停獵手_{datetime.now().strftime('%Y%m%d_%H%M')}.csv","text/csv",use_container_width=True)
        elif lr is not None and lr.empty:
            st.info(f"無評分 ≥ {st.session_state.p_min_score} 的候選股，可降低最低顯示評分")
        else:
            st.warning("尚未掃描，請點擊左側「套用參數重新掃描」")

    st.markdown('</div>', unsafe_allow_html=True)

# ── 底部 ──────────────────────────────────────────────────
st.markdown(f"""
<div style="padding:12px 24px;border-top:1px solid var(--border);display:flex;justify-content:space-between;font-size:0.73em;color:var(--dim);">
  <span>台股掃描器　｜　資料來源：TWSE / TPEX</span>
  <span>{'🟢 交易中' if mkt_open else '⚫ 休市'}　{now_tw.strftime('%Y-%m-%d %H:%M')}</span>
</div>""", unsafe_allow_html=True)
