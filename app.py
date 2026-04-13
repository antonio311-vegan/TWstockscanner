# ============================================================
# 📊 台股掃描器 v6 — 三策略儀表板
# 單頁三欄佈局：主力訊號 | 三刀流 | 漲停獵手
# 各策略卡片顯示快訊，點擊展開細節
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
# 全域 CSS — 軍事指揮中心風格
# ════════════════════════════════════════════════════════════

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Noto+Sans+TC:wght@300;400;700&display=swap');

:root {
  --bg:      #070b0f;
  --bg2:     #0d1520;
  --border:  #1a3050;
  --accent1: #00c8ff;
  --accent2: #ff6b35;
  --accent3: #39ff14;
  --warn:    #ffcc00;
  --danger:  #ff2244;
  --text:    #c8d8e8;
  --dim:     #4a6080;
}

html, body, [data-testid="stAppViewContainer"] {
  background: var(--bg) !important;
  color: var(--text) !important;
  font-family: 'Noto Sans TC', sans-serif !important;
}

[data-testid="stHeader"] { background: transparent !important; }

.stButton > button {
  background: transparent !important;
  border: 1px solid var(--accent1) !important;
  color: var(--accent1) !important;
  font-family: 'Share Tech Mono', monospace !important;
  letter-spacing: 1px;
  transition: all 0.2s;
}
.stButton > button:hover {
  background: var(--accent1) !important;
  color: var(--bg) !important;
}

[data-testid="stExpander"] {
  background: var(--bg2) !important;
  border: 1px solid var(--border) !important;
  border-radius: 4px !important;
}

.stDataFrame { background: var(--bg2) !important; }

/* 隱藏 Streamlit 預設元素 */
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }
[data-testid="stSidebar"] { display: none !important; }
.block-container { padding: 1rem 1.5rem !important; max-width: 100% !important; }
</style>

<style>
/* ─── 頂部狀態欄 ─── */
.topbar {
  display: flex; align-items: center; justify-content: space-between;
  background: var(--bg2); border-bottom: 1px solid var(--border);
  padding: 10px 20px; margin: -1rem -1.5rem 1.5rem;
  font-family: 'Share Tech Mono', monospace;
}
.topbar-title { color: var(--accent1); font-size: 1.1em; letter-spacing: 3px; }
.topbar-time  { color: var(--accent3); font-size: 0.9em; }
.topbar-mkt   { font-size: 0.85em; }

/* ─── 策略卡片 ─── */
.strategy-card {
  background: var(--bg2);
  border: 1px solid var(--border);
  border-top: 3px solid;
  border-radius: 6px;
  padding: 18px 20px 14px;
  height: 100%;
  position: relative;
  transition: border-color 0.3s;
}
.strategy-card.blue  { border-top-color: var(--accent1); }
.strategy-card.orange{ border-top-color: var(--accent2); }
.strategy-card.green { border-top-color: var(--accent3); }

.card-label {
  font-family: 'Share Tech Mono', monospace;
  font-size: 0.7em; letter-spacing: 3px;
  color: var(--dim); margin-bottom: 4px;
}
.card-title { font-size: 1.15em; font-weight: 700; margin-bottom: 14px; }
.blue  .card-title { color: var(--accent1); }
.orange.card-title, .orange .card-title { color: var(--accent2); }
.green .card-title { color: var(--accent3); }

.card-stat {
  display: flex; justify-content: space-between;
  border-top: 1px solid var(--border); padding-top: 10px; margin-top: 10px;
}
.stat-item { text-align: center; }
.stat-num  { font-family: 'Share Tech Mono', monospace; font-size: 1.8em; font-weight: 700; }
.stat-lbl  { font-size: 0.7em; color: var(--dim); }
.blue  .stat-num { color: var(--accent1); }
.orange.stat-num, .orange .stat-num { color: var(--accent2); }
.green .stat-num { color: var(--accent3); }

/* ─── 快訊條目 ─── */
.alert-item {
  padding: 6px 10px; margin: 4px 0;
  border-left: 3px solid; border-radius: 0 4px 4px 0;
  font-size: 0.85em; cursor: pointer;
  background: rgba(255,255,255,0.03);
  transition: background 0.15s;
}
.alert-item:hover { background: rgba(255,255,255,0.07); }
.alert-item.blue   { border-left-color: var(--accent1); }
.alert-item.orange { border-left-color: var(--accent2); }
.alert-item.green  { border-left-color: var(--accent3); }
.alert-item.danger { border-left-color: var(--danger); }

/* ─── 漲停閃爍警報 ─── */
@keyframes limitFlash {
  0%,100% { background: #2a0000; border-color: var(--danger); }
  50%     { background: #500000; border-color: #ff6666; }
}
.limit-alert {
  animation: limitFlash 1s infinite;
  border: 2px solid var(--danger); border-radius: 6px;
  padding: 10px 16px; margin: 8px 0;
  font-family: 'Share Tech Mono', monospace;
}

/* ─── 評分徽章 ─── */
.score-badge {
  display: inline-block; padding: 2px 8px; border-radius: 3px;
  font-family: 'Share Tech Mono', monospace; font-size: 0.85em; font-weight: 700;
}
.score-high   { background: rgba(255,107,53,0.2);  color: var(--accent2); border: 1px solid var(--accent2); }
.score-mid    { background: rgba(0,200,255,0.15);  color: var(--accent1); border: 1px solid var(--accent1); }
.score-low    { background: rgba(57,255,20,0.12);  color: var(--accent3); border: 1px solid var(--accent3); }
.score-danger { background: rgba(255,34,68,0.2);   color: var(--danger);  border: 1px solid var(--danger); }

.divider { border: none; border-top: 1px solid var(--border); margin: 16px 0; }
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
# 頂部狀態欄
# ════════════════════════════════════════════════════════════

mkt_open = is_trading()
now_tw   = tw_now()
weekday_zh = ["一","二","三","四","五","六","日"]

st.markdown(f"""
<div class="topbar">
  <div class="topbar-title">📊 台股掃描器　TAIWAN STOCK SCANNER</div>
  <div class="topbar-time">⏱ {now_tw.strftime('%Y-%m-%d %H:%M:%S')} (台灣)</div>
  <div class="topbar-mkt">
    {'<span style="color:var(--accent3);">● 交易中</span>' if mkt_open else '<span style="color:var(--dim);">● 休市</span>'}
    　星期{weekday_zh[now_tw.weekday()]}
  </div>
</div>
""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 資料載入函數
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
            results.append({"代號":sid,"名稱":row.get("stock_name",""),
                "收盤":row["close"],"漲跌(%)":chg,
                "五日均週轉(%)":round(t_avg,3),"今日週轉(%)":round(t_now,3),
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
    zw=("⚠️ 負斜率" if neg_s else "✅ 正斜率") if signal in ["🔴 三刀做多","🟡 反彈做多"] else ("⚠️ 正斜率" if pos_s else "✅ 負斜率")
    return {"信號":signal,"收盤":round(price,2),"240MA":round(m240,2),"60MA":round(m60,2),"20MA":round(m20,2),
            "vs240MA":"✅" if ab240 else "❌","vs60MA":"✅" if ab60 else "❌","張飛":zw}

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
        nm["代號"]=nm["代號"].str.strip()
        return dict(zip(nm["代號"],nm["名稱"]))
    except: return {}

# ════════════════════════════════════════════════════════════
# AI 推薦
# ════════════════════════════════════════════════════════════

def ai_recommend(df_r, scan_type):
    if df_r is None or df_r.empty: return None
    rows_str=df_r.head(15).to_string(index=False)
    prompt=f"""你是台股專業投資人，20年經驗。掃描信號：{scan_type}
清單：\n{rows_str}
選最值得關注的一檔。只回覆JSON：
{{"stock_id":"代號","name":"名稱","signal":"信號","reason":"理由40字內繁體中文","key_point":"操作重點25字內","confidence":"高/中/低","risk":"高/中/低"}}"""
    try:
        resp=requests.post("https://api.anthropic.com/v1/messages",
            headers={"Content-Type":"application/json"},
            json={"model":"claude-sonnet-4-20250514","max_tokens":300,"messages":[{"role":"user","content":prompt}]},timeout=25)
        text=resp.json()["content"][0]["text"].strip()
        return json.loads(text.replace("```json","").replace("```","").strip())
    except Exception as e: return {"error":str(e)}

def show_ai_card(rec, accent="var(--accent1)"):
    if not rec or "error" in rec: return
    cf={"高":"🟢","中":"🟡","低":"🔴"}.get(rec.get("confidence","中"),"🟡")
    rk={"高":"🔴","中":"🟡","低":"🟢"}.get(rec.get("risk","中"),"🟡")
    st.markdown(f"""
<div style="background:linear-gradient(135deg,#0a0f15,#0d1520);border:1px solid {accent};
border-radius:6px;padding:16px;margin:12px 0;">
<div style="color:{accent};font-size:0.7em;letter-spacing:3px;font-family:'Share Tech Mono',monospace;">
🤖 AI RECOMMENDATION</div>
<div style="color:white;font-size:1.3em;font-weight:700;margin:6px 0;">
  {rec.get('stock_id','')} {rec.get('name','')}
  <span style="background:{accent};color:#000;font-size:0.4em;padding:2px 8px;border-radius:3px;margin-left:8px;vertical-align:middle;font-family:'Share Tech Mono',monospace;">⭐ MARK</span>
</div>
<div style="color:#889aaa;font-size:0.85em;margin:4px 0;"><span style="color:#ccc;">信號：</span>{rec.get('signal','')}</div>
<div style="color:#889aaa;font-size:0.85em;margin:4px 0;"><span style="color:#ccc;">理由：</span>{rec.get('reason','')}</div>
<div style="color:#889aaa;font-size:0.85em;margin:4px 0;"><span style="color:#ccc;">操作：</span>{rec.get('key_point','')}</div>
<div style="display:flex;gap:16px;margin-top:8px;font-size:0.8em;">
  <span>信心：{cf} {rec.get('confidence','')}</span>
  <span>風險：{rk} {rec.get('risk','')}</span>
</div>
<div style="color:#3a4a5a;font-size:0.7em;margin-top:8px;">⚠️ 僅供參考，不構成投資建議</div>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# Session State 初始化
# ════════════════════════════════════════════════════════════

for key in ["force_result","force_latest","force_time",
            "sword_result","sword_time",
            "limit_result","limit_time"]:
    if key not in st.session_state: st.session_state[key] = None

# ════════════════════════════════════════════════════════════
# 三欄策略卡片
# ════════════════════════════════════════════════════════════

col1, col2, col3 = st.columns(3, gap="medium")

# ── 欄 1：主力進場訊號 ─────────────────────────────────────
with col1:
    fr  = st.session_state.force_result
    cnt = len(fr) if fr is not None and len(fr)>0 else 0
    ft  = st.session_state.force_time or "—"

    st.markdown(f"""
<div class="strategy-card blue">
  <div class="card-label">STRATEGY 01</div>
  <div class="card-title">🎯 主力進場訊號</div>
  <div style="color:var(--dim);font-size:0.8em;margin-bottom:10px;">沉寂股突然爆量，主力可能進場布局</div>
  <div style="font-size:0.75em;color:var(--dim);">最後掃描：{ft}</div>
  <div class="card-stat">
    <div class="stat-item blue">
      <div class="stat-num blue">{cnt}</div>
      <div class="stat-lbl">符合股票</div>
    </div>
    <div class="stat-item">
      <div class="stat-num" style="color:var(--accent3);font-size:1.2em;">
        {'🔴 有訊號' if cnt>0 else '⚫ 無訊號'}
      </div>
      <div class="stat-lbl">當前狀態</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    run_force = st.button("🔍 掃描主力訊號", use_container_width=True, key="btn_force")

    # 快訊預覽
    if fr is not None and len(fr) > 0:
        st.markdown(f"<div style='margin:8px 0 4px;font-size:0.75em;color:var(--dim);'>快訊（{len(fr)} 檔）</div>", unsafe_allow_html=True)
        for _, row in fr.head(5).iterrows():
            chg = row.get("漲跌(%)","")
            color = "danger" if float(chg)>5 else "blue"
            st.markdown(f"""
<div class="alert-item {color}">
  <span style="color:white;font-weight:700;">{row['代號']}</span>
  <span style="color:#889aaa;margin:0 6px;">{row.get('名稱','')[:6]}</span>
  <span style="color:var(--accent1);">週轉{row['今日週轉(%)']}%</span>
  <span style="color:var(--warn);margin-left:6px;">{row['週轉倍數']}x</span>
  <span style="color:{'var(--danger)' if float(chg)>0 else 'var(--accent3)'};float:right;">{'+' if float(chg)>0 else ''}{chg}%</span>
</div>""", unsafe_allow_html=True)
        if len(fr) > 5:
            st.markdown(f"<div style='color:var(--dim);font-size:0.75em;text-align:center;padding:4px;'>... 還有 {len(fr)-5} 檔，展開查看</div>", unsafe_allow_html=True)

# ── 欄 2：三刀流 ──────────────────────────────────────────
with col2:
    sr  = st.session_state.sword_result
    s_counts = {}
    if sr is not None and len(sr) > 0:
        s_counts = sr["信號"].value_counts().to_dict()
    total_sword = sum(s_counts.values())
    sword_t = st.session_state.sword_time or "—"

    st.markdown(f"""
<div class="strategy-card orange">
  <div class="card-label">STRATEGY 02</div>
  <div class="card-title">⚔️ 三刀流（60分K）</div>
  <div style="color:var(--dim);font-size:0.8em;margin-bottom:10px;">🟠240MA 🟢60MA 🔵20MA 均線信號</div>
  <div style="font-size:0.75em;color:var(--dim);">最後掃描：{sword_t}</div>
  <div class="card-stat">
    <div class="stat-item">
      <div class="stat-num" style="color:var(--accent2);">{s_counts.get('🔴 三刀做多',0)}</div>
      <div class="stat-lbl">三刀做多</div>
    </div>
    <div class="stat-item">
      <div class="stat-num" style="color:var(--warn);">{s_counts.get('🟡 反彈做多',0)}</div>
      <div class="stat-lbl">反彈做多</div>
    </div>
    <div class="stat-item">
      <div class="stat-num" style="color:var(--accent1);">{total_sword}</div>
      <div class="stat-lbl">合計</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    run_sword = st.button("⚔️ 掃描三刀流", use_container_width=True, key="btn_sword")

    # 快訊預覽
    if sr is not None and len(sr) > 0:
        st.markdown(f"<div style='margin:8px 0 4px;font-size:0.75em;color:var(--dim);'>快訊（{len(sr)} 檔）</div>", unsafe_allow_html=True)
        sig_colors = {"🔴 三刀做多":"danger","🟡 反彈做多":"orange","🟣 修正做空":"blue","🔵 三刀做空":"blue"}
        for _, row in sr.head(5).iterrows():
            sc = sig_colors.get(row.get("信號",""), "orange")
            st.markdown(f"""
<div class="alert-item {sc}">
  <span style="color:white;font-weight:700;">{row['代號']}</span>
  <span style="color:#889aaa;margin:0 6px;">{row.get('名稱','')[:6]}</span>
  <span style="color:var(--accent2);font-size:0.9em;">{row.get('信號','')}</span>
  <span style="color:var(--dim);float:right;font-size:0.85em;">{row.get('張飛','')}</span>
</div>""", unsafe_allow_html=True)
        if len(sr) > 5:
            st.markdown(f"<div style='color:var(--dim);font-size:0.75em;text-align:center;padding:4px;'>... 還有 {len(sr)-5} 檔，展開查看</div>", unsafe_allow_html=True)

# ── 欄 3：漲停獵手 ────────────────────────────────────────
with col3:
    lr     = st.session_state.limit_result
    lt     = st.session_state.limit_time or "—"
    lim70  = len(lr[lr["評分"]>=70]) if lr is not None and len(lr)>0 else 0
    lim_hit= len(lr[lr.get("已漲停","")=="🚨 是"]) if lr is not None and len(lr)>0 and "已漲停" in lr.columns else 0

    st.markdown(f"""
<div class="strategy-card green">
  <div class="card-label">STRATEGY 03</div>
  <div class="card-title">🎯 漲停獵手</div>
  <div style="color:var(--dim);font-size:0.8em;margin-bottom:10px;">綜合評分預測漲停潛力股</div>
  <div style="font-size:0.75em;color:var(--dim);">最後掃描：{lt}</div>
  <div class="card-stat">
    <div class="stat-item">
      <div class="stat-num" style="color:var(--accent2);">{lim70}</div>
      <div class="stat-lbl">高分70+</div>
    </div>
    <div class="stat-item">
      <div class="stat-num" style="color:var(--danger);">{lim_hit}</div>
      <div class="stat-lbl">已漲停</div>
    </div>
    <div class="stat-item">
      <div class="stat-num" style="color:var(--accent3);">{len(lr) if lr is not None else 0}</div>
      <div class="stat-lbl">候選總數</div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    run_limit = st.button("🎯 掃描漲停獵手", use_container_width=True, key="btn_limit")

    # 快訊預覽
    if lr is not None and len(lr) > 0:
        st.markdown(f"<div style='margin:8px 0 4px;font-size:0.75em;color:var(--dim);'>快訊（高分 {lim70} 檔）</div>", unsafe_allow_html=True)
        top_lr = lr.sort_values("評分", ascending=False).head(5)
        for _, row in top_lr.iterrows():
            sc  = row.get("評分", 0)
            scl = "danger" if sc>=70 else "green" if sc>=50 else "blue"
            already = row.get("已漲停","")
            st.markdown(f"""
<div class="alert-item {scl}">
  <span style="color:white;font-weight:700;">{row['代號']}</span>
  <span style="color:#889aaa;margin:0 6px;">{str(row.get('名稱',''))[:5]}</span>
  {f'<span class="score-badge score-high">{sc}分</span>' if sc>=70 else f'<span class="score-badge score-mid">{sc}分</span>'}
  {f'<span style="color:var(--danger);margin-left:6px;">🚨漲停</span>' if already=="🚨 是" else ""}
  <span style="color:var(--dim);float:right;font-size:0.85em;">{row.get("觸發條件","")[:20]}</span>
</div>""", unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 分隔線
# ════════════════════════════════════════════════════════════

st.markdown('<hr class="divider">', unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════
# 展開詳情區（點擊掃描後自動展開）
# ════════════════════════════════════════════════════════════

# ── 掃描執行邏輯 ──────────────────────────────────────────

if run_force:
    with st.spinner("📡 載入歷史資料..."):
        try: df_hist = get_main_data()
        except Exception as e: st.error(f"❌ {e}"); df_hist = None

    if df_hist is not None:
        with st.spinner("🔍 掃描主力訊號..."):
            rdf, latest = scan_main_force(df_hist)
        st.session_state.force_result = rdf
        st.session_state.force_latest = latest
        st.session_state.force_time   = tw_now_str()
        st.rerun()

if run_sword:
    with st.spinner("📋 取得股票清單..."):
        try:
            r=requests.get("https://openapi.twse.com.tw/v1/opendata/t187ap03_L",timeout=15,headers=HEADERS,verify=False)
            sid_list=[s.strip() for s in pd.DataFrame(r.json())["公司代號"].tolist() if s.strip().isdigit()][:300]
        except: sid_list=[]
    results2=[]; total=len(sid_list)
    prog=st.progress(0,"⚔️ 掃描三刀流..."); BATCH=25
    for bs in range(0,total,BATCH):
        batch=sid_list[bs:bs+BATCH]; tickers=[s+".TW" for s in batch]
        prog.progress(int(bs/total*100)/100,f"⚔️ {bs}/{total}...")
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
    prog.progress(1.0,"✅ 完成")
    if results2:
        rdf2=pd.DataFrame(results2)
        nm=get_name_map(); rdf2["名稱"]=rdf2["代號"].map(nm).fillna("")
        col_order=["信號","市場","代號","名稱","收盤","240MA","60MA","20MA","vs240MA","vs60MA","張飛"]
        rdf2=rdf2[[c for c in col_order if c in rdf2.columns]]
        st.session_state.sword_result = rdf2
        st.session_state.sword_time   = tw_now_str()
    st.rerun()

if run_limit:
    with st.spinner("📡 載入資料..."):
        try: df_hist=get_main_data()
        except Exception as e: st.error(f"❌ {e}"); df_hist=None

    if df_hist is not None:
        # 主力訊號
        rdf_force,_=scan_main_force(df_hist)
        force_ids=set(rdf_force["代號"].tolist()) if len(rdf_force)>0 else set()

        # 歷史技術評分
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
            elif 5<=chg<7:  score+=10; flags.append(f"📊{chg:.1f}%")
            if row["close"]>high5: score+=15; flags.append("🎯高點")
            if bull_ma: score+=10; flags.append("📐多頭")

            # 即時報價加分（開盤中）
            rt={}
            if is_trading():
                rt_batch=get_twse_realtime([sid])
                rt=rt_batch.get(sid,{})
                if rt.get("已漲停"): score+=50; flags.append("🚨漲停")
                elif rt.get("距漲停(%)","")!="" and float(rt.get("距漲停(%)",99))<1: score+=35; flags.append("⚡<1%")
                elif rt.get("距漲停(%)","")!="" and float(rt.get("距漲停(%)",99))<3: score+=20; flags.append("⚡<3%")
                if rt.get("漲幅(%)",0)>7: score+=15; flags.append(f"📈{rt.get('漲幅(%)',0):.1f}%")

            if score>=25:
                scores.append({"評分":min(score,100),"代號":sid,
                    "名稱":nm.get(sid,""),"昨收":row["close"],
                    "現價":rt.get("現價","-"),"漲幅(%)":rt.get("漲幅(%)",chg),
                    "距漲停(%)":rt.get("距漲停(%)","-"),
                    "漲停價":rt.get("漲停價",round(row["close"]*1.1,1)),
                    "已漲停":"🚨 是" if rt.get("已漲停") else "",
                    "觸發條件":" | ".join(flags)})

        lr=pd.DataFrame(scores).sort_values("評分",ascending=False).reset_index(drop=True) if scores else pd.DataFrame()
        st.session_state.limit_result=lr
        st.session_state.limit_time=tw_now_str()
        st.rerun()

# ════════════════════════════════════════════════════════════
# 詳情展開區
# ════════════════════════════════════════════════════════════

fr = st.session_state.force_result
sr = st.session_state.sword_result
lr = st.session_state.limit_result

# 已漲停緊急警報（全寬顯示）
if lr is not None and len(lr)>0 and "已漲停" in lr.columns:
    hits=lr[lr["已漲停"]=="🚨 是"]
    if len(hits)>0:
        hit_list=" ｜ ".join([f"{r['代號']} {r['名稱']}" for _,r in hits.iterrows()])
        st.markdown(f"""
<div class="limit-alert">
  <span style="color:var(--danger);font-size:1.2em;font-family:'Share Tech Mono',monospace;">
    🚨 LIMIT UP DETECTED — 已漲停 {len(hits)} 檔
  </span>
  <div style="color:white;margin-top:6px;">{hit_list}</div>
</div>""", unsafe_allow_html=True)

# ── 主力訊號詳情 ──────────────────────────────────────────
if fr is not None:
    with st.expander(f"📋 主力進場訊號詳情　— 共 {len(fr)} 檔　（點擊展開 / 收起）",
                     expanded=(len(fr)>0)):
        if len(fr)>0:
            # AI 推薦
            ai_col, data_col = st.columns([1,2])
            with ai_col:
                with st.spinner("🤖 AI 分析..."):
                    rec=ai_recommend(fr,"主力進場訊號")
                show_ai_card(rec, "var(--accent1)")
            with data_col:
                def cc(v): return f"color:{'#ff4444' if v>0 else '#44ff88' if v<0 else '#888'}"
                st.dataframe(fr.style.applymap(cc,subset=["漲跌(%)"]),
                             use_container_width=True, height=350)
                csv=fr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("💾 下載 CSV",csv,
                    f"主力訊號_{st.session_state.force_latest.strftime('%Y%m%d') if st.session_state.force_latest else 'data'}.csv",
                    "text/csv")
        else:
            st.info("此交易日無符合條件的股票")

# ── 三刀流詳情 ────────────────────────────────────────────
if sr is not None:
    sig_order=["🔴 三刀做多","🟡 反彈做多","🟣 修正做空","🔵 三刀做空"]
    total_s=len(sr)
    with st.expander(f"⚔️ 三刀流詳情　— 共 {total_s} 檔　（點擊展開 / 收起）",
                     expanded=(total_s>0)):
        if total_s>0:
            ai_col2, data_col2 = st.columns([1,2])
            with ai_col2:
                with st.spinner("🤖 AI 分析..."):
                    rec2=ai_recommend(sr,"三刀流多頭信號")
                show_ai_card(rec2, "var(--accent2)")
            with data_col2:
                # 信號分類顯示
                sig_tabs = st.tabs([f"{s}（{len(sr[sr['信號']==s])}）" for s in sig_order if len(sr[sr['信號']==s])>0])
                active_sigs = [s for s in sig_order if len(sr[sr['信號']==s])>0]
                for tab_, sig in zip(sig_tabs, active_sigs):
                    with tab_:
                        sub=sr[sr["信號"]==sig].drop(columns=["信號"])
                        st.dataframe(sub, use_container_width=True, height=280)
            csv2=sr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("💾 下載三刀流 CSV",csv2,
                f"三刀流_{datetime.now().strftime('%Y%m%d_%H%M')}.csv","text/csv")
        else:
            st.info("目前無符合三刀流條件的股票")

# ── 漲停獵手詳情 ──────────────────────────────────────────
if lr is not None:
    lim70=len(lr[lr["評分"]>=70]) if len(lr)>0 else 0
    with st.expander(f"🎯 漲停獵手詳情　— 高分 {lim70} 檔 ／ 共 {len(lr)} 檔　（點擊展開 / 收起）",
                     expanded=(lim70>0)):
        if len(lr)>0:
            ai_col3, data_col3 = st.columns([1,2])
            with ai_col3:
                with st.spinner("🤖 AI 分析..."):
                    rec3=ai_recommend(lr.head(15),"漲停潛力股")
                show_ai_card(rec3, "var(--accent3)")
                # 評分分布
                st.markdown("**評分分布**")
                bins=[0,30,50,70,100]; labels=["<30","30-50","50-70","70+"]
                lr["區間"]=pd.cut(lr["評分"],bins=bins,labels=labels)
                dist=lr["區間"].value_counts().reindex(labels)
                for label,clr in zip(labels,["#3a4a5a","#0088ff","#88ff00","#ff6b35"]):
                    cnt_=dist.get(label,0)
                    st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;margin:4px 0;">
  <div style="width:60px;font-size:0.8em;color:#888;">{label}</div>
  <div style="flex:1;background:#111;border-radius:3px;overflow:hidden;height:16px;">
    <div style="width:{int(cnt_/max(len(lr),1)*100)}%;background:{clr};height:100%;"></div>
  </div>
  <div style="width:30px;text-align:right;color:{clr};font-family:'Share Tech Mono',monospace;">{cnt_}</div>
</div>""", unsafe_allow_html=True)
                if "區間" in lr.columns: lr=lr.drop(columns=["區間"])

            with data_col3:
                # 按分數分級顯示
                score_tabs = st.tabs(["🔥 70+分", "⚡ 50-70分", "📊 30-50分", "📋 全部"])
                with score_tabs[0]:
                    st.dataframe(lr[lr["評分"]>=70],use_container_width=True,height=250)
                with score_tabs[1]:
                    st.dataframe(lr[(lr["評分"]>=50)&(lr["評分"]<70)],use_container_width=True,height=250)
                with score_tabs[2]:
                    st.dataframe(lr[(lr["評分"]>=30)&(lr["評分"]<50)],use_container_width=True,height=250)
                with score_tabs[3]:
                    st.dataframe(lr,use_container_width=True,height=250)

            csv3=lr.to_csv(index=False,encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button("💾 下載漲停獵手 CSV",csv3,
                f"漲停獵手_{datetime.now().strftime('%Y%m%d_%H%M')}.csv","text/csv")
        else:
            st.info("目前無符合條件的候選股票")

# ── 底部狀態 ──────────────────────────────────────────────
st.markdown(f"""
<div style="margin-top:24px;padding:10px 0;border-top:1px solid var(--border);
display:flex;justify-content:space-between;font-size:0.75em;color:var(--dim);
font-family:'Share Tech Mono',monospace;">
  <span>台股掃描器 v6　|　資料來源：TWSE / TPEX / TWSE MIS</span>
  <span>{'🟢 市場交易中' if mkt_open else '⚫ 休市'}　{now_tw.strftime('%Y-%m-%d %H:%M')}</span>
</div>""", unsafe_allow_html=True)
