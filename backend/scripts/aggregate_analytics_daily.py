#!/usr/bin/env python3
"""
Aggregate analytics_events → analytics_daily
Run daily via cron: 0 1 * * * cd /path/to/backend && python scripts/aggregate_analytics_daily.py
Or: python scripts/aggregate_analytics_daily.py 2026-01-15
"""
import os
import sys
from datetime import datetime, timedelta, timezone, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

load_dotenv()

from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_SERVICE_KEY")
if not url or not key:
    print("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
    sys.exit(1)

client = create_client(url, key)


def aggregate_date(target_date: date):
    start = datetime.combine(target_date, datetime.min.time()).replace(tzinfo=timezone.utc)
    end = start + timedelta(days=1)

    r = (
        client.table("analytics_events")
        .select("id,event_type,session_id,shop_domain,brand_id,event_data")
        .gte("created_at", start.isoformat())
        .lt("created_at", end.isoformat())
        .execute()
    )
    events = r.data or []

    groups: dict[tuple, dict] = {}
    for e in events:
        brand_id = e.get("brand_id")
        shop = e.get("shop_domain") or "_unknown"
        key_t = (brand_id, shop)
        if key_t not in groups:
            groups[key_t] = {
                "tryons_started": 0,
                "add_to_carts": 0,
                "purchases": 0,
                "sessions": set(),
                "revenue": 0.0,
            }
        g = groups[key_t]
        et = e.get("event_type") or ""
        if et == "tryon_started":
            g["tryons_started"] += 1
        elif et == "add_to_cart":
            g["add_to_carts"] += 1
        elif et == "purchase":
            g["purchases"] += 1
            ed = e.get("event_data") or {}
            g["revenue"] += float(ed.get("amount") or 0)
        sid = e.get("session_id")
        if sid:
            g["sessions"].add(str(sid))

    for (brand_id, shop), g in groups.items():
        shop_val = None if shop == "_unknown" else shop
        row = {
            "brand_id": brand_id,
            "shop_domain": shop_val,
            "date": target_date.isoformat(),
            "tryons_started": g["tryons_started"],
            "add_to_carts": g["add_to_carts"],
            "purchases": g["purchases"],
            "unique_sessions": len(g["sessions"]),
            "revenue": round(g["revenue"], 2),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }

        # Delete existing row for this scope + date (upsert)
        try:
            q = client.table("analytics_daily").delete().eq("date", target_date.isoformat())
            if brand_id:
                q = q.eq("brand_id", brand_id)
            else:
                q = q.is_("brand_id", "null")
                if shop_val is not None:
                    q = q.eq("shop_domain", shop_val)
                else:
                    q = q.is_("shop_domain", "null")
            q.execute()
        except Exception:
            pass

        ins = {k: v for k, v in row.items() if k != "updated_at"}
        try:
            client.table("analytics_daily").insert(ins).execute()
        except Exception as ex:
            print(f"Insert error: {ex}")

    print(f"Aggregated {target_date}: {len(groups)} groups, {len(events)} events")


if __name__ == "__main__":
    if len(sys.argv) > 1:
        d = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    else:
        d = date.today() - timedelta(days=1)
    aggregate_date(d)
