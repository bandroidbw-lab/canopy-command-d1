from flask import Flask, render_template_string, request, redirect, url_for
import os
import requests
from supabase import create_client, Client
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime

app = Flask(__name__)

# Initialize Supabase client
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# --- AUTOMATED BACKGROUND SPATIAL HARVESTER TASK ---
def scheduled_spatial_harvest():
    print(f"[{datetime.now()}] [CRON] Automated background job triggered: Harvesting Overpass spatial leads...")
    try:
        overpass_query = """
        [out:json][timeout:25];
        area[name="Costilla County"]->.searchArea;
        (
          way["building"](area.searchArea);
          way["natural"="tree"](area.searchArea);
        );
        out body;
        >;
        out skel qt;
        """
        response = requests.post(OVERPASS_URL, data={'data': overpass_query})
        if response.status_code == 200:
            data = response.json()
            elements = data.get("elements", [])
            print(f"[CRON SUCCESS] Harvested {len(elements)} raw spatial elements.")
            
            scored_leads = []
            for el in elements:
                if el.get("type") == "way" and "tags" in el:
                    tags = el["tags"]
                    if "building" in tags:
                        lead_record = {
                            "parcel_id": f"CC-{el.get('id')}",
                            "name": f"Property near {tags.get('addr:street', 'San Luis Valley Route')}",
                            "confidence_rating": 4.1,
                            "star_rating": "★★★★☆",
                            "status": "Ready for D1 Queue"
                        }
                        if lead_record["confidence_rating"] >= 3.0:
                            scored_leads.append(lead_record)
            
            for lead in scored_leads:
                supabase.table("lead_queue").upsert(lead).execute()
            print(f"[{datetime.now()}] [CRON SUCCESS] Synced {len(scored_leads)} high-confidence leads to Supabase queue.")
        else:
            print(f"[CRON ERROR] Overpass API failed with status code: {response.status_code}")
    except Exception as e:
        print(f"[{datetime.now()}] [CRON ERROR] Spatial harvest exception: {str(e)}")

scheduler = BackgroundScheduler()
scheduler.add_job(func=scheduled_spatial_harvest, trigger="cron", hour=2, minute=0)
scheduler.start()

import atexit
atexit.register(lambda: scheduler.shutdown())


NAV_BAR = """
<nav style="background: #1e1e1e; padding: 10px; margin-bottom: 20px; border-bottom: 2px solid #00ff66;">
    <a href="/" style="color: #00ff66; margin-right: 15px; text-decoration: none; font-weight: bold;">[D1: Command Center & Scoreboard]</a>
    <a href="/queue" style="color: #00ff66; margin-right: 15px; text-decoration: none; font-weight: bold;">[Smart Queue & 3-Star+ Leads]</a>
    <a href="/assisted" style="color: #00ff66; margin-right: 15px; text-decoration: none; font-weight: bold;">[Assisted Tiers & Time Tracking]</a>
    <a href="/contractors" style="color: #00ff66; margin-right: 15px; text-decoration: none; font-weight: bold;">[Contractor Financial Groups]</a>
    <a href="/reports" style="color: #00ff66; text-decoration: none; font-weight: bold;">[Manual Reports Search]</a>
</nav>
"""

BASE_STYLE = """
<style>
    body { font-family: monospace; background: #121212; color: #00ff66; padding: 20px; margin: 0; }
    h1, h2 { color: #fff; border-bottom: 1px solid #333; padding-bottom: 8px; }
    .card { background: #1e1e1e; border: 1px solid #333; padding: 15px; margin-bottom: 15px; border-radius: 5px; }
    .grid-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 15px; margin-bottom: 20px; }
    .stat-box { background: #181818; border: 1px solid #00ff66; padding: 15px; text-align: center; border-radius: 5px; }
    .stat-number { font-size: 1.8em; color: #fff; font-weight: bold; }
    table { width: 100%; border-collapse: collapse; margin-top: 10px; background: #181818; }
    th, td { border: 1px solid #333; padding: 10px; text-align: left; color: #ddd; }
    th { background: #222; color: #00ff66; }
    .btn { background: #00ff66; color: #121212; padding: 8px 12px; border: none; font-weight: bold; cursor: pointer; text-decoration: none; display: inline-block; }
    .badge { background: #333; color: #ffaa00; padding: 3px 6px; font-size: 0.8em; border-radius: 3px; }
    .input-field { background: #222; border: 1px solid #444; color: #fff; padding: 8px; width: 100%; margin-bottom: 10px; box-sizing: border-box; }
</style>
"""

@app.route("/")
def d1_command_center():
    scoreboard = {
        "d2_reports": 14,
        "sets": 8,
        "drops": 5,
        "callbacks": 6,
        "d5_presentations": 4,
        "sold": 3,
        "resets": 2,
        "daily_revenue": "$1,450.00",
        "potential_payments": "$3,200.00",
        "active_queue_count": 32
    }
    
    return render_template_string(BASE_STYLE + NAV_BAR + """
    <h1>D1 Master Command Center & Live Scoreboard <span class="badge">Cloud Operational</span></h1>
    
    <div class="card">
        <h3>Real-Time Pipeline Scoreboard</h3>
        <div class="grid-stats">
            <div class="stat-box"><div>D2 Reports</div><div class="stat-number">{{ sb.d2_reports }}</div></div>
            <div class="stat-box"><div>Sets</div><div class="stat-number">{{ sb.sets }}</div></div>
            <div class="stat-box"><div>Drops</div><div class="stat-number">{{ sb.drops }}</div></div>
            <div class="stat-box"><div>Callbacks</div><div class="stat-number">{{ sb.callbacks }}</div></div>
            <div class="stat-box"><div>D5 Presentations</div><div class="stat-number">{{ sb.d5_presentations }}</div></div>
            <div class="stat-box" style="border-color: #ff3333;"><div>SOLD / Closed</div><div class="stat-number" style="color: #ff3333;">{{ sb.sold }}</div></div>
            <div class="stat-box"><div>Resets</div><div class="stat-number">{{ sb.resets }}</div></div>
        </div>
    </div>
    """, sb=scoreboard)

@app.route("/queue", methods=["GET", "POST"])
def d1_queue_manager():
    return render_template_string(BASE_STYLE + NAV_BAR + "<h1>Lead Queue & Smart Filler</h1>")

@app.route("/assisted")
def d1_assisted_tiers():
    return render_template_string(BASE_STYLE + NAV_BAR + "<h1>Assisted Tiers</h1>")

@app.route("/contractors")
def d1_contractor_groups():
    return render_template_string(BASE_STYLE + NAV_BAR + "<h1>Contractor Groups</h1>")

@app.route("/reports")
def d1_reports_search():
    return render_template_string(BASE_STYLE + NAV_BAR + "<h1>Manual Reports</h1>")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)