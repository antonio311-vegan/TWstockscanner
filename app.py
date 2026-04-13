# ============================================================
# 📊 台股掃描器 v7 — 白色主題 + 三策略同步執行
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
# 白色主題 CSS
# ════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@300;400;500;700&family=JetBrains+Mono:wght@400;600&display=swap');

:root {
  --bg:       #ffffff;
  --bg2:      #f8f9fc;
  --bg3:      #f0f2f7;
  --border:   #e2e6ef;
  --text:     #1a2035;
  --dim:      #7a8499;
  --c1:       #0070f3;   /* 主力訊號：藍 */
  --c1-bg:    #eff6ff;
  --c2:       #f97316;   /* 三刀流：橘 */
  --c2-bg:    #fff7ed;
  --c3:       #16a34a;   /* 漲停獵手：綠 */
  --c3-bg:    #f0fdf4;
  --danger:   #dc2626;
  --warn:     #d97706;
  --shadow:   0 2px 12px rgba(0,0,0,0.08);
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Noto Sans TC', sans-serif !important;
}
[data-testid="stHeader"]    { background: white !important; border-bottom: 1px solid var(--border); }
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebar"]   { display: none !important; }
.block-container { padding: 0 !important; max-width: 100% !important; }

/* Streamlit 元件覆蓋 */
.stButton > button {
  background: white !important; border: 1.5px solid var(--border) !important;
  color: var(--text) !important; font-family: 'Noto Sans TC', sans-serif !important;
  border-radius: 8px !important; font-size: 0.88em !important;
  transition: all 0.18s !important;
}
.stButton > button:hover { border-color: var(--c1) !important; color: var(--c1) !important; background: var(--c1-bg) !important; }

[data-testid="stExpander"] {
  background: white !important; border: 1px solid var(--border) !important;
  border-radius: 10px !important; box-shadow: var(--shadow) !important;
}
[data-testid="stExpander"] summary {
  font-weight: 600 !important; color: var(--text) !important;
}

.stTabs [data-baseweb="tab-list"] { background: var(--bg2) !important; border-radius: 8px !important; }
.stTabs [data-baseweb="tab"]      { color: var(--dim) !important; }
.stTabs [aria-selected="true"]    { color: var(--text) !important; font-weight: 600 !important; }

.stDataFrame { border: 1px solid var(--border) !important; border-radius: 8px !important; }

/* 進度條 */
.stProgress > div > div { background: var(--c1) !important; }
</style>

<style>
/* ─── 頂部欄 ─── */
.topbar {
  background: white; border-bottom: 1px solid var(--border);
  padding: 12px 28px; display: flex; align-items: center;
  justify-content: space-between; position: sticky; top: 0; z-index: 100;
}
.topbar-brand { display: flex; align-items: center; gap: 10px; }
.topbar-icon  { width: 32px; height: 32px; background: var(--c1); border-radius: 8px;
  display: flex; align-items: center; justify-content: center; color: white; font-size: 1.1em; }
.topbar-title { font-size: 1em; font-weight: 700; color: var(--text); letter-spacing: 0.5px; }
.topbar-sub   { font-size: 0.75em; color: var(--dim); }
.topbar-time  { font-family: 'JetBrains Mono', monospace; font-size: 0.85em; color: var(--dim); }
.mkt-badge    { padding: 4px 12px; border-radius: 20px; font-size: 0.8em; font-weight: 600; }
.mkt-open     { background: #dcfce7; color: #16a34a; }
.mkt-closed   { background: var(--bg3); color: var(--dim); }

/* ─── 主要容器 ─── */
.main-wrap { padding: 24px 28px; }

/* ─── 全部掃描按鈕 ─── */
.scan-all-btn {
  width: 100%; padding: 14px; border-radius: 12px;
  background: linear-gradient(135deg, var(--c1), #0050cc);
  color: white; border: none; font-size: 1em; font-weight: 600;
  cursor: pointer; letter-spacing: 0.5px;
  box-shadow: 0 4px 14px rgba(0,112,243,0.35);
  transition: all 0.2s;
}
.scan-all-btn:hover { transform: translateY(-1px); box-shadow: 0 6px 20px rgba(0,112,243,0.45); }

/* ─── 策略卡片 ─── */
.s-card {
  background: white; border: 1px solid var(--border);
  border-radius: 12px; padding: 20px;
  box-shadow: var(--shadow); height: 100%;
  border-top: 4px solid;
}
.s-card.c1 { border-top-color: var(--c1); }
.s-card.c2 { border-top-color: var(--c2); }
.s-card.c3 { border-top-color: var(--c3); }

.s-tag  { font-size: 0.68em; font-weight: 700; letter-spacing: 2px; color: var(--dim); margin-bottom: 6px; }
.s-name { font-size: 1.1em; font-weight: 700; margin-bottom: 4px; }
.c1 .s-name { color: var(--c1); }
.c2 .s-name { color: var(--c2); }
.c3 .s-name { color: var(--c3); }
.s-desc { font-size: 0.8em; color: var(--dim); margin-bottom: 14px; }

.s-stats { display: flex; gap: 0; border-top: 1px solid var(--border); padding-top: 14px; margin-top: 4px; }
.s-stat  { flex: 1; text-align: center; }
.s-stat + .s-stat { border-left: 1px solid var(--border); }
.s-num   { font-family: 'JetBrains Mono', monospace; font-size: 1.8em; font-weight: 700; }
.c1 .s-num { color: var(--c1); }
.c2 .s-num { color: var(--c2); }
.c3 .s-num { color: var(--c3); }
.num-danger { color: var(--danger) !important; }
.s-lbl  { font-size: 0.7em; color: var(--dim); margin-top: 2px; }

/* ─── 掃描狀態指示 ─── */
.scan-status {
  display: flex; align-items: center; gap: 6px;
  font-size: 0.75em; color: var(--dim); margin-bottom: 10px;
}
.dot { width: 7px; height: 7px; border-radius: 50%; display: inline-block; }
.dot-green  { background: var(--c3); box-shadow: 0 0 6px var(--c3); }
.dot-grey   { background: #ccc; }
.dot-pulse  { background: var(--c1); animation: pulse-dot 1s infinite; }
@keyframes pulse-dot { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }

/* ─── 快訊列表 ─── */
.alert-list { margin-top: 10px; }
.alert-row {
  display: flex; align-items: center; gap: 8px;
  padding: 7px 10px; border-radius: 7px; margin-bottom: 4px;
  background: var(--bg2); font-size: 0.83em;
  border-left: 3px solid transparent;
  transition: background 0.15s;
}
.alert-row:hover { background: var(--bg3); }
.alert-row.c1 { border-left-color: var(--c1); }
.alert-row.c2 { border-left-color: var(--c2); }
.alert-row.c3 { border-left-color: var(--c3); }
.alert-row.cdanger { border-left-color: var(--danger); }
.a-code  { font-family: 'JetBrains Mono', monospace; font-weight: 700; color: var(--text); min-width: 42px; }
.a-name  { color: var(--dim); flex: 1; }
.a-sig   { font-size: 0.9em; }
.a-val   { font-family: 'JetBrains Mono', monospace; margin-left: auto; }
.text-up    { color: var(--danger); }
.text-down  { color: var(--c3); }
.text-c1    { color: var(--c1); }
.text-c2    { color: var(--c2); }
.text-c3    { color: var(--c3); }
.text-warn  { color: var(--warn); }
.text-dim   { color: var(--dim); }

/* ─── 漲停警報橫幅 ─── */
@keyframes banner-flash { 0%,100%{background:#fee2e2} 50%{background:#fecaca} }
.limit-banner {
  animation: banner-flash 1.5s infinite;
  border: 1.5px solid var(--danger); border-radius: 10px;
  padding: 12px 18px; margin: 16px 0;
  display: flex; align-items: center; gap: 12px;
}
.limit-banner .lbl { font-weight: 700; color: var(--danger); font-size: 0.9em; }
.limit-banner .stocks { color: var(--text); font-size: 0.85em; }

/* ─── AI 推薦卡 ─── */
.ai-card {
  background: var(--bg2); border: 1px solid var(--border);
  border-radius: 10px; padding: 16px; margin-bottom: 12px;
}
.ai-tag  { font-size: 0.7em; font-weight: 700; letter-spacing: 2px; color: var(--dim); margin-bottom: 8px; }
.ai-name { font-size: 1.15em; font-weight: 700; color: var(--text); margin-bottom: 4px; }
.ai-mark { background: var(--c1); color: white; font-size: 0.6em; padding: 2px 7px;
  border-radius: 4px; margin-left: 8px; vertical-align: middle; }
.ai-row  { font-size: 0.83em; color: var(--dim); margin: 3px 0; }
.ai-row strong { color: var(--text); }
.ai-badges { display: flex; gap: 8px; margin-top: 8px; }
.badge { padding: 3px 10px; border-radius: 5px; font-size: 0.78em; font-weight: 600; }
.badge-high { background: #dcfce7; color: #16a34a; }
.badge-mid  { background: #fef9c3; color: #854d0e; }
.badge-low  { background: #fee2e2; color: #991b1b; }
.ai-disclaimer { font-size: 0.7em; color: #aaa; margin-top: 8px; }

/* ─── 分隔線 ─── */
.divider { border: none; border-top: 1px solid var(--border); margin: 20px 0; }

/* ─── 詳情標題 ─── */
.detail-hdr {
  display: flex; align-items: center; gap: 10px;
  padding: 14px 18px; background: var(--bg2);
  border-radius: 10px 10px 0 0; border-bottom: 1px solid var(--border);
}
.detail-hdr .dot-color { width: 10px; height: 10px; border-radius: 50%; }
</style>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 共用工具
# ════════════════════════════════════════════════════════════

def clean_num(s):
    if isinstance(s, pd.DataFrame): s = s.iloc[:, 0]
    return pd.to_numeric(
        pd.Series(s).astype(str).str.replace(",","").str.replace(" ","").str.strip(),
        errors="coerce")

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

# ════════════════════════════════════════════════════════════
# Session State 初始化
# ════════════════════════════════════════════════════════════

for k,v in [("force_result",None),("force_latest",None),("force_time","—"),
            ("sword_result",None),("sword_time","—"),
            ("limit_result",None),("limit_time","—"),
            ("scanning_all",False),("scan_step","")]:
    if k not in st.session_state: st.session_state[k]=v

# ════════════════════════════════════════════════════════════
# 頂部欄
# ════════════════════════════════════════════════════════════

mkt_open = is_trading()
now_tw   = tw_now()
weekday_zh = ["一","二","三","四","五","六","日"]

st.markdown(f"""
<div class="topbar">
  <div class="topbar-brand">
    <div class="topbar-icon">📊</div>
    <div>
      <div class="topbar-title">台股掃描器</div>
      <div class="topbar-sub">TAIWAN STOCK SCANNER</div>
    </div>
  </div>
  <div class="topbar-time">
    {now_tw.strftime('%Y-%m-%d %H:%M:%S')}　星期{weekday_zh[now_tw.weekday()]}
  </div>
  <div>
    <span class="mkt-badge {'mkt-open' if mkt_open else 'mkt-closed'}">
      {'● 交易中' if mkt_open else '● 休市'}
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown('<div class="main-wrap">', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 資料層函數
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

def scan_main_force(df, t1=1.0, t2=2.5, tm=3.0, vm=2.0, vx=5.0):
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
    if len(rdf)>0: rdf=rdf.sort_values("週轉倍數",ascending=False).reset_index(drop=True)
    return rdf, latest

def calc_three_sword(df_p, cross_n=2, slope_n=3,
    sig_types=["🔴 三刀做多","🟡 反彈做多","🟣 修正做空","🔵 三刀做空"]):
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

def get_twse_realtime(stock_ids):
    results={}; BATCH=50
    for bs in range(0,len(stock_ids),BATCH):
        batch=stock_ids[bs:bs+BATCH]
        ex_ch="|".join([f"tse_{sid}.tw" for sid in batch])
        url=f"https://mis.twse.com.tw/stock/api/getStockInfo.jsp?ex_ch={ex_ch}&json=1&delay=0"
        try:
            resp=requests.get(url,timeout=10,headers={"User-Agent":"Mozilla/5.0","Referer":"https://mis.twse.com.tw/"},verify=False)
            for item in resp.json().get("msgArray",[]):
                sid=item.get("c",""); price=float(item.get("z",0) or 0)
                limit=float(item.get("w",0) or 0); prev=float(item.get("y",0) or 0)
                vol=float(item.get("v",0) or 0)
                if price>0 and limit>0 and prev>0:
                    results[sid]={"現價":price,"漲停價":limit,"昨收":prev,
                        "距漲停(%)":round((limit-price)/price*100,2),
                        "漲幅(%)":round((price-prev)/prev*100,2),
                        "成交量":int(vol),"已漲停":abs(price-limit)<0.01}
        except: pass
        time.sleep(0.3)
    return results

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
選最值得關注的一檔。只回覆JSON：
{{"stock_id":"代號","name":"名稱","signal":"信號","reason":"理由40字內繁體中文","key_point":"操作重點20字內","confidence":"高/中/低","risk":"高/中/低"}}"""
    try:
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":280,"messages":[{"role":"user","content":prompt}]},timeout=25)
        text=resp.json()["content"][0]["text"].strip()
        return json.loads(text.replace("```json","").replace("```","").strip())
    except Exception as e: return {"error":str(e)}

def show_ai_card(rec, color="#0070f3"):
    if not rec or "error" in rec: return
    cf_cls={"高":"badge-high","中":"badge-mid","低":"badge-low"}.get(rec.get("confidence","中"),"badge-mid")
    rk_cls={"高":"badge-low","中":"badge-mid","低":"badge-high"}.get(rec.get("risk","中"),"badge-mid")
    st.markdown(f"""
<div class="ai-card">
  <div class="ai-tag">🤖 AI RECOMMENDATION</div>
  <div class="ai-name">
    {rec.get('stock_id','')} {rec.get('name','')}
    <span class="ai-mark">⭐ MARK</span>
  </div>
  <div class="ai-row"><strong>信號：</strong>{rec.get('signal','')}</div>
  <div class="ai-row"><strong>理由：</strong>{rec.get('reason','')}</div>
  <div class="ai-row"><strong>操作：</strong>{rec.get('key_point','')}</div>
  <div class="ai-badges">
    <span class="badge {cf_cls}">信心：{rec.get('confidence','')}</span>
    <span class="badge {rk_cls}">風險：{rec.get('risk','')}</span>
  </div>
  <div class="ai-disclaimer">⚠️ 僅供參考，不構成投資建議</div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 三大策略核心掃描函數（供全部掃描呼叫）
# ════════════════════════════════════════════════════════════

def run_scan_force(df_hist):
    rdf, latest = scan_main_force(df_hist)
    st.session_state.force_result = rdf
    st.session_state.force_latest = latest
    st.session_state.force_time   = tw_now_str()

def run_scan_sword():
    try:
        r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",timeout=15,headers=HEADERS,verify=False)
        sid_list=[s.strip() for s in pd.DataFrame(r.json())["公司代號"].tolist() if s.strip().isdigit()][:250]
    except: sid_list=[]
    results2=[]; total=len(sid_list); BATCH=25
    prog_ph = st.empty()
    for bs in range(0,total,BATCH):
        batch=sid_list[bs:bs+BATCH]; tickers=[s+".TW" for s in batch]
        prog_ph.progress(int(bs/total*100)/100, f"⚔️ 三刀流 {bs}/{total}...")
        try:
            raw=yf.download(tickers,period="60d",interval="60m",group_by="ticker",auto_adjust=True,progress=False,threads=True)
        except: continue
        for yc in tickers:
            sid=yc.split(".")[0]
            try:
                df_p=raw[yc] if len(tickers)>1 else raw
                if df_p is None or df_p.empty or "Close" not in df_p.columns: continue
                res=calc_three_sword(df_p.dropna(subset=["Close"]))
                if res: res["代號"]=sid; res["市場"]="上市"; results2.append(res)
            except: pass
        time.sleep(0.3)
    prog_ph.empty()
    if results2:
        rdf2=pd.DataFrame(results2)
        nm=get_name_map(); rdf2["名稱"]=rdf2["代號"].map(nm).fillna("")
        col_order=["信號","市場","代號","名稱","收盤","240MA","60MA","20MA","vs240MA","vs60MA","張飛"]
        rdf2=rdf2[[c for c in col_order if c in rdf2.columns]]
        st.session_state.sword_result=rdf2
    else:
        st.session_state.sword_result=pd.DataFrame()
    st.session_state.sword_time=tw_now_str()

def run_scan_limit(df_hist):
    rdf_force,_=scan_main_force(df_hist)
    force_ids=set(rdf_force["代號"].tolist()) if len(rdf_force)>0 else set()
    latest=df_hist["date"].max(); today=df_hist[df_hist["date"]==latest].copy()
    prev_day=df_hist[df_hist["date"]<latest].groupby("stock_id").last()
    nm=get_name_map(); scores=[]
    for sid, row in today.set_index("stock_id").iterrows():
        prev=prev_day.loc[sid] if sid in prev_day.index else None
        chg=round((row["close"]-prev["close"])/prev["close"]*100,2) if prev is not None and prev["close"]>0 else 0
        recent=df_hist[df_hist["stock_id"]==sid].tail(6)
        high5=recent["close"].iloc[:-1].max() if len(recent)>1 else 0
        closes=df_hist[df_hist["stock_id"]==sid].tail(10)["close"].values
        bull_ma=(len(closes)>=10 and closes[-1]>closes[-5:].mean()>closes.mean())
        score=0; flags=[]
        if sid in force_ids: score+=30; flags.append("📈主力")
        if 7<=chg<9.5: score+=20; flags.append(f"🔥{chg:.1f}%")
        elif 5<=chg<7: score+=10; flags.append(f"📊{chg:.1f}%")
        if row["close"]>high5: score+=15; flags.append("🎯高點")
        if bull_ma: score+=10; flags.append("📐多頭")
        if is_trading():
            rt_batch=get_twse_realtime([sid]); rt=rt_batch.get(sid,{})
            if rt.get("已漲停"): score+=50; flags.append("🚨漲停")
            elif rt.get("距漲停(%)","")!="" and float(rt.get("距漲停(%)",99))<1: score+=35; flags.append("⚡<1%")
            elif rt.get("距漲停(%)","")!="" and float(rt.get("距漲停(%)",99))<3: score+=20; flags.append("⚡<3%")
            if rt.get("漲幅(%)",0)>7: score+=15; flags.append(f"📈{rt.get('漲幅(%)',0):.1f}%")
        if score>=25:
            scores.append({"評分":min(score,100),"代號":sid,"名稱":nm.get(sid,""),
                "昨收":row["close"],"漲停價":round(row["close"]*1.1,1),
                "已漲停":"","觸發條件":" | ".join(flags)})
    lr=pd.DataFrame(scores).sort_values("評分",ascending=False).reset_index(drop=True) if scores else pd.DataFrame()
    st.session_state.limit_result=lr
    st.session_state.limit_time=tw_now_str()

# ════════════════════════════════════════════════════════════
# 全部掃描按鈕區
# ════════════════════════════════════════════════════════════

btn_col1, btn_col2, btn_col3, btn_col4 = st.columns([2,1,1,1])
with btn_col1:
    scan_all = st.button("🚀 全部掃描（三策略同步執行）",
                         type="primary", use_container_width=True, key="scan_all")
with btn_col2:
    run_force_only = st.button("🎯 主力訊號", use_container_width=True, key="btn_force")
with btn_col3:
    run_sword_only = st.button("⚔️ 三刀流", use_container_width=True, key="btn_sword")
with btn_col4:
    run_limit_only = st.button("🎯 漲停獵手", use_container_width=True, key="btn_limit")

# ════════════════════════════════════════════════════════════
# 三欄策略卡片
# ════════════════════════════════════════════════════════════

st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3, gap="medium")

# 取得各策略結果
fr      = st.session_state.force_result
sr      = st.session_state.sword_result
lr      = st.session_state.limit_result
force_t = st.session_state.force_time
sword_t_val = st.session_state.sword_time
limit_t = st.session_state.limit_time

force_cnt = len(fr) if fr is not None and len(fr)>0 else 0
sword_cnt = len(sr) if sr is not None and len(sr)>0 else 0
s_counts  = sr["信號"].value_counts().to_dict() if sr is not None and len(sr)>0 else {}
lim70     = len(lr[lr["評分"]>=70]) if lr is not None and len(lr)>0 else 0
lim_hit   = len(lr[lr["已漲停"]=="🚨 是"]) if lr is not None and len(lr)>0 and "已漲停" in lr.columns else 0

with col1:
    dot_cls = "dot-green" if force_cnt>0 else "dot-grey"
    st.markdown(f"""
<div class="s-card c1">
  <div class="s-tag">STRATEGY 01</div>
  <div class="s-name">🎯 主力進場訊號</div>
  <div class="s-desc">沉寂股突然爆量，主力可能進場布局</div>
  <div class="scan-status">
    <span class="dot {dot_cls}"></span>
    <span>最後掃描：{force_t}</span>
  </div>
  <div class="s-stats">
    <div class="s-stat"><div class="s-num c1">{force_cnt}</div><div class="s-lbl">符合股票</div></div>
    <div class="s-stat"><div class="s-num" style="color:{'var(--danger)' if force_cnt>3 else 'var(--c1)'};">{'🔴 活躍' if force_cnt>0 else '⚫ 無訊號'}</div><div class="s-lbl">狀態</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    if fr is not None and force_cnt>0:
        st.markdown('<div class="alert-list">', unsafe_allow_html=True)
        for _, row in fr.head(4).iterrows():
            chg=float(row.get("漲跌(%)","0") or 0)
            st.markdown(f"""
<div class="alert-row c1">
  <span class="a-code">{row['代號']}</span>
  <span class="a-name">{str(row.get('名稱',''))[:5]}</span>
  <span class="text-c1">{row['今日週轉(%)']}%</span>
  <span class="a-val text-warn">{row['週轉倍數']}x</span>
  <span class="a-val {'text-up' if chg>0 else 'text-down'}">{'+' if chg>0 else ''}{chg:.1f}%</span>
</div>""", unsafe_allow_html=True)
        if force_cnt>4:
            st.markdown(f'<div style="font-size:0.75em;color:var(--dim);text-align:center;padding:4px;">↓ 還有 {force_cnt-4} 檔，展開查看</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with col2:
    dot_cls2 = "dot-green" if sword_cnt>0 else "dot-grey"
    st.markdown(f"""
<div class="s-card c2">
  <div class="s-tag">STRATEGY 02</div>
  <div class="s-name">⚔️ 三刀流（60分K）</div>
  <div class="s-desc">🟠 240MA　🟢 60MA　🔵 20MA</div>
  <div class="scan-status">
    <span class="dot {dot_cls2}"></span>
    <span>最後掃描：{sword_t_val}</span>
  </div>
  <div class="s-stats">
    <div class="s-stat"><div class="s-num c2">{s_counts.get('🔴 三刀做多',0)}</div><div class="s-lbl">三刀做多</div></div>
    <div class="s-stat"><div class="s-num" style="color:var(--warn);">{s_counts.get('🟡 反彈做多',0)}</div><div class="s-lbl">反彈做多</div></div>
    <div class="s-stat"><div class="s-num c2">{sword_cnt}</div><div class="s-lbl">合計</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    if sr is not None and sword_cnt>0:
        sig_c={"🔴 三刀做多":"cdanger","🟡 反彈做多":"c2","🟣 修正做空":"c1","🔵 三刀做空":"c1"}
        st.markdown('<div class="alert-list">', unsafe_allow_html=True)
        for _, row in sr.head(4).iterrows():
            sc=sig_c.get(row.get("信號",""),"c2")
            st.markdown(f"""
<div class="alert-row {sc}">
  <span class="a-code">{row['代號']}</span>
  <span class="a-name">{str(row.get('名稱',''))[:5]}</span>
  <span class="a-sig text-c2">{row.get('信號','')}</span>
  <span class="a-val text-dim" style="font-size:0.8em;">{row.get('張飛','')}</span>
</div>""", unsafe_allow_html=True)
        if sword_cnt>4:
            st.markdown(f'<div style="font-size:0.75em;color:var(--dim);text-align:center;padding:4px;">↓ 還有 {sword_cnt-4} 檔，展開查看</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

with col3:
    dot_cls3 = "dot-green" if lim70>0 else "dot-grey"
    st.markdown(f"""
<div class="s-card c3">
  <div class="s-tag">STRATEGY 03</div>
  <div class="s-name">🎯 漲停獵手</div>
  <div class="s-desc">綜合評分預測漲停潛力股</div>
  <div class="scan-status">
    <span class="dot {dot_cls3}"></span>
    <span>最後掃描：{limit_t}</span>
  </div>
  <div class="s-stats">
    <div class="s-stat"><div class="s-num c3">{lim70}</div><div class="s-lbl">高分70+</div></div>
    <div class="s-stat"><div class="s-num {'num-danger' if lim_hit>0 else 'c3'}">{lim_hit}</div><div class="s-lbl">已漲停</div></div>
    <div class="s-stat"><div class="s-num c3">{len(lr) if lr is not None else 0}</div><div class="s-lbl">候選總數</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    if lr is not None and len(lr)>0:
        st.markdown('<div class="alert-list">', unsafe_allow_html=True)
        for _, row in lr.sort_values("評分",ascending=False).head(4).iterrows():
            sc2=row.get("評分",0)
            scl="cdanger" if sc2>=70 else "c3"
            already=row.get("已漲停","")
            st.markdown(f"""
<div class="alert-row {scl}">
  <span class="a-code">{row['代號']}</span>
  <span class="a-name">{str(row.get('名稱',''))[:5]}</span>
  <span class="badge {'badge-low' if sc2>=70 else 'badge-high'}" style="font-size:0.75em;">{sc2}分</span>
  {'<span class="text-up" style="font-size:0.8em;">🚨漲停</span>' if already=="🚨 是" else ""}
  <span class="a-val text-dim" style="font-size:0.8em;">{str(row.get("觸發條件",""))[:12]}</span>
</div>""", unsafe_allow_html=True)
        if len(lr)>4:
            st.markdown(f'<div style="font-size:0.75em;color:var(--dim);text-align:center;padding:4px;">↓ 還有 {len(lr)-4} 檔，展開查看</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 執行掃描（全部 or 單一）
# ════════════════════════════════════════════════════════════

do_force = scan_all or run_force_only
do_sword = scan_all or run_sword_only
do_limit = scan_all or run_limit_only

if do_force or do_sword or do_limit:
    st.markdown('<hr class="divider">', unsafe_allow_html=True)

    # 需要歷史資料的策略先載入
    df_hist = None
    if do_force or do_limit:
        with st.spinner("📡 載入歷史資料（TWSE / TPEX）..."):
            try: df_hist = get_main_data()
            except Exception as e: st.error(f"❌ 歷史資料載入失敗：{e}")

    # 同步執行各策略（依序，但在同一畫面顯示進度）
    prog_container = st.container()
    with prog_container:
        if scan_all:
            st.markdown("### 🚀 三策略同步掃描中...")
            p1, p2, p3 = st.columns(3)

        if do_force and df_hist is not None:
            label = "1/3 主力進場訊號" if scan_all else "掃描主力訊號"
            with st.spinner(f"🎯 {label}..."):
                run_scan_force(df_hist)
            if scan_all:
                with p1: st.success(f"✅ 主力訊號完成　{len(st.session_state.force_result)} 檔")

        if do_sword:
            label = "2/3 三刀流" if scan_all else "掃描三刀流"
            st.markdown(f"**⚔️ {label}（上市前250檔，約3～5分鐘）**")
            run_scan_sword()
            if scan_all:
                with p2: st.success(f"✅ 三刀流完成　{len(st.session_state.sword_result or [])} 檔")

        if do_limit and df_hist is not None:
            label = "3/3 漲停獵手" if scan_all else "掃描漲停獵手"
            with st.spinner(f"🎯 {label}..."):
                run_scan_limit(df_hist)
            if scan_all:
                with p3: st.success(f"✅ 漲停獵手完成　{len(st.session_state.limit_result or [])} 檔")

    st.rerun()

# ════════════════════════════════════════════════════════════
# 詳情展開區
# ════════════════════════════════════════════════════════════

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# 漲停警報橫幅
if lr is not None and len(lr)>0 and "已漲停" in lr.columns:
    hits=lr[lr["已漲停"]=="🚨 是"]
    if len(hits)>0:
        hit_str=" ｜ ".join([f"{r['代號']} {r['名稱']}" for _,r in hits.iterrows()])
        st.markdown(f"""
<div class="limit-banner">
  <span style="font-size:1.5em;">🚨</span>
  <div><div class="lbl">已漲停 {len(hits)} 檔</div>
  <div class="stocks">{hit_str}</div></div>
</div>""", unsafe_allow_html=True)

# ── 主力訊號詳情 ──────────────────────────────────────────
if fr is not None:
    with st.expander(f"🎯 主力進場訊號詳情　{force_cnt} 檔", expanded=force_cnt>0):
        if force_cnt>0:
            ai_c, data_c = st.columns([1,2])
            with ai_c:
                with st.spinner("🤖 AI 分析..."): rec=ai_recommend(fr,"主力進場訊號")
                show_ai_card(rec,"#0070f3")
            with data_c:
                def cc1(v):
                    try: return f"color:{'#dc2626' if float(v)>0 else '#16a34a' if float(v)<0 else '#888'}"
                    except: return ""
                st.dataframe(fr.style.applymap(cc1,subset=["漲跌(%)"]),use_container_width=True,height=350)
                csv=fr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("💾 下載 CSV",csv,f"主力_{st.session_state.force_latest.strftime('%Y%m%d') if st.session_state.force_latest else 'data'}.csv","text/csv")
        else:
            st.info("此交易日無符合條件的股票")

# ── 三刀流詳情 ────────────────────────────────────────────
if sr is not None:
    with st.expander(f"⚔️ 三刀流詳情　{sword_cnt} 檔", expanded=sword_cnt>0):
        if sword_cnt>0:
            ai_c2, data_c2 = st.columns([1,2])
            with ai_c2:
                with st.spinner("🤖 AI 分析..."): rec2=ai_recommend(sr,"三刀流多頭信號")
                show_ai_card(rec2,"#f97316")
            with data_c2:
                sig_order=["🔴 三刀做多","🟡 反彈做多","🟣 修正做空","🔵 三刀做空"]
                active=[s for s in sig_order if len(sr[sr["信號"]==s])>0]
                tabs_=st.tabs([f"{s}（{len(sr[sr['信號']==s])}）" for s in active])
                for tab_,sig in zip(tabs_,active):
                    with tab_: st.dataframe(sr[sr["信號"]==sig].drop(columns=["信號"]),use_container_width=True,height=260)
            csv2=sr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("💾 下載三刀流 CSV",csv2,f"三刀流_{datetime.now().strftime('%Y%m%d_%H%M')}.csv","text/csv")
        else:
            st.info("目前無符合三刀流條件的股票")

# ── 漲停獵手詳情 ──────────────────────────────────────────
if lr is not None:
    with st.expander(f"🎯 漲停獵手詳情　高分 {lim70} 檔 / 共 {len(lr)} 檔", expanded=lim70>0):
        if len(lr)>0:
            ai_c3, data_c3 = st.columns([1,2])
            with ai_c3:
                with st.spinner("🤖 AI 分析..."): rec3=ai_recommend(lr.head(12),"漲停潛力股")
                show_ai_card(rec3,"#16a34a")
                st.markdown("**評分分布**")
                for label,clr,rng in [("70+","#dc2626",(70,101)),("50-70","#f97316",(50,70)),("30-50","#0070f3",(30,50))]:
                    cnt_=len(lr[(lr["評分"]>=rng[0])&(lr["評分"]<rng[1])])
                    pct=int(cnt_/max(len(lr),1)*100)
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:8px;margin:4px 0;font-size:0.83em;">
  <span style="width:45px;color:#888;">{label}</span>
  <div style="flex:1;background:#f0f2f7;border-radius:3px;height:14px;">
    <div style="width:{pct}%;background:{clr};height:100%;border-radius:3px;"></div>
  </div>
  <span style="width:25px;color:{clr};font-weight:700;text-align:right;">{cnt_}</span>
</div>""", unsafe_allow_html=True)
            with data_c3:
                t70,t50,t30,tall=st.tabs(["🔥 70+","⚡ 50-70","📊 30-50","📋 全部"])
                with t70:  st.dataframe(lr[lr["評分"]>=70],use_container_width=True,height=240)
                with t50:  st.dataframe(lr[(lr["評分"]>=50)&(lr["評分"]<70)],use_container_width=True,height=240)
                with t30:  st.dataframe(lr[(lr["評分"]>=30)&(lr["評分"]<50)],use_container_width=True,height=240)
                with tall: st.dataframe(lr,use_container_width=True,height=240)
            csv3=lr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("💾 下載漲停獵手 CSV",csv3,f"漲停獵手_{datetime.now().strftime('%Y%m%d_%H%M')}.csv","text/csv")
        else:
            st.info("目前無符合條件的候選股票")

# ── 底部 ──────────────────────────────────────────────────
st.markdown(f"""
<hr class="divider">
<div style="display:flex;justify-content:space-between;font-size:0.75em;color:var(--dim);padding-bottom:16px;">
  <span>台股掃描器　|　資料來源：TWSE / TPEX / TWSE MIS</span>
  <span>{'🟢 市場交易中' if mkt_open else '⚫ 休市'}　{now_tw.strftime('%Y-%m-%d %H:%M')}</span>
</div>
""", unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)
