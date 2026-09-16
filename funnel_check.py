#!/usr/bin/env python3
"""Chequeo automatico del embudo Google Ads -> chat -> cita (ElHilar). Telegram a Pablo.
Creado 2026-06-21 tras parches de embudo (Lever 2). Rolling 7 dias."""
import os, json, subprocess, urllib.request, collections, datetime as dt

# --- creds ---
env={}
try:
    for ln in open("/opt/elhilar-bot/.env"):
        ln=ln.strip()
        if "=" in ln and not ln.startswith("#"):
            k,v=ln.split("=",1); env[k]=v.strip().strip('"').strip("'")
except Exception: pass
def from_container(var):
    try:
        out=subprocess.check_output(["docker","exec","elhilar-nurture","printenv",var],timeout=15)
        return out.decode().strip()
    except Exception: return ""
SUPA=env.get("SUPABASE_SERVICE_KEY") or from_container("SUPABASE_SERVICE_KEY")
TG=env.get("TELEGRAM_BOT_TOKEN") or from_container("TELEGRAM_BOT_TOKEN")
CHAT=env.get("TELEGRAM_CHAT_ID_PABLO") or from_container("TELEGRAM_CHAT_ID_PABLO")
B="https://qdozsmoeknytzqennrww.supabase.co/rest/v1"
def sq(p):
    r=urllib.request.Request(B+"/"+p,headers={"apikey":SUPA,"Authorization":"Bearer "+SUPA})
    return json.load(urllib.request.urlopen(r,timeout=40))

cut7=(dt.datetime.utcnow()-dt.timedelta(days=7)).strftime("%Y-%m-%d")

# --- Google Ads 7d ---
ads_line="Ads: (error)"
try:
    from google.ads.googleads.client import GoogleAdsClient
    c=GoogleAdsClient.load_from_storage("/opt/google-ads-mcp/env/google-ads.yaml"); c.login_customer_id="9934575843"
    g=c.get_service("GoogleAdsService")
    for r in g.search(customer_id="8813881007", query="SELECT metrics.cost_micros, metrics.clicks, metrics.conversions, campaign.bidding_strategy_type FROM campaign WHERE campaign.id=23922692090 AND segments.date DURING LAST_7_DAYS"):
        m=r.metrics
        ads_line=f"Ads 7d: ${m.cost_micros/1e6:,.0f} | {m.clicks} clk | {m.conversions:.0f} conv | puja={r.campaign.bidding_strategy_type.name}"
except Exception as e:
    ads_line=f"Ads: error {str(e)[:60]}"

# --- wa_ref_codes 7d ---
rows=sq(f"wa_ref_codes?select=landing,claimed_at,created_at&created_at=gte.{cut7}T00:00:00")
by=collections.defaultdict(lambda:[0,0])
for x in rows:
    L=x.get("landing") or "?"; by[L][0]+=1
    if x.get("claimed_at"): by[L][1]+=1
land=sum(v[0] for v in by.values()); conv=sum(v[1] for v in by.values())
land_lines="\n".join(f"  {L}: {t}→{cc}" for L,(t,cc) in sorted(by.items(),key=lambda kv:-kv[1][0])[:4])

# --- pipeline_conversations origin=google_ads 7d ---
pc=sq(f"pipeline_conversations?select=phase,meeting_time,booking_link_sent,last_message_at&origin=eq.google_ads&last_message_at=gte.{cut7}T00:00:00")
ph=collections.Counter(c.get("phase") for c in pc)
booked=sum(1 for c in pc if c.get("phase")=="BOOKED")
mt=sum(1 for c in pc if c.get("meeting_time"))
blink=sum(1 for c in pc if c.get("booking_link_sent"))
proposing=ph.get("PROPOSING",0)

# --- veredicto ---
flag="🟢" if (booked>0 or mt>0) else ("🟡" if proposing>0 or blink>0 else "🔴")
msg=(f"<b>{flag} Embudo Google Ads — ElHilar (7d)</b>\n"
     f"{ads_line}\n\n"
     f"<b>Aterrizajes→conversación:</b> {land}→{conv} ({(conv/land*100 if land else 0):.1f}%)\n{land_lines}\n\n"
     f"<b>Conversaciones de ads:</b> {len(pc)}\n"
     f"  fases: {dict(ph)}\n"
     f"  booking link enviado: {blink} | PROPOSING: {proposing} | <b>BOOKED: {booked}</b> | con cita(meeting_time): {mt}\n\n"
     f"Baseline 21-jun (30d): 514→7→0 citas, 1/7 link. Meta: ver BOOKED/cita &gt; 0.")

if TG and CHAT:
    body=json.dumps({"chat_id":CHAT,"text":msg,"parse_mode":"HTML","disable_web_page_preview":True}).encode()
    req=urllib.request.Request(f"https://api.telegram.org/bot{TG}/sendMessage",data=body,headers={"Content-Type":"application/json"})
    print("telegram:", urllib.request.urlopen(req,timeout=20).getcode())
else:
    print("NO telegram creds"); print(msg)
