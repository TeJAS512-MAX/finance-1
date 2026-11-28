import httpx
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
import email.utils
from typing import List
from intelligence.event_radar import event_radar
import asyncio

WATCHLIST = ['RELIANCE', 'INFY', 'TCS', 'SBIN', 'ZOMATO', 'ITC', 'ICICIBANK', 'WIPRO', 'HDFCBANK', 'BAJFINANCE']

async def ingest_public_news():
    """
    Fetches real public news for the watchlist from Yahoo Finance RSS.
    Validates timestamps, extracts events, and adds them to the Event Radar DB.
    """
    # Yahoo Finance format: RELIANCE.NS
    tickers = ",".join([f"{sym}.NS" for sym in WATCHLIST])
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={tickers}"
    
    try:
        async with httpx.AsyncClient(timeout=10.0, headers={'User-Agent': 'Mozilla/5.0'}) as client:
            response = await client.get(url)
            response.raise_for_status()
            content = response.content
            
        root = ET.fromstring(content)
        channel = root.find("channel")
        if channel is None:
            return
            
        new_events = 0
        for item in channel.findall("item"):
            title = item.find("title").text if item.find("title") is not None else ""
            link = item.find("link").text if item.find("link") is not None else ""
            pubDate = item.find("pubDate").text if item.find("pubDate") is not None else ""
            
            # Map ticker back to symbol
            # This is a naive mapping since Yahoo might not strictly tag the symbol in the item
            # We'll check if our symbols appear in the title or if there's a symbol tag
            matched_symbols = []
            for sym in WATCHLIST:
                if sym.lower() in title.lower() or sym in title:
                    matched_symbols.append(sym)
                    
            if not matched_symbols:
                # Fallback: maybe we can just assign it to all if it's macro? 
                # Better to just skip if we can't attribute it to a specific symbol.
                continue
                
            # Parse pubDate (RFC 2822 format)
            try:
                dt_tuple = email.utils.parsedate_tz(pubDate)
                if dt_tuple:
                    dt = datetime(*dt_tuple[:6], tzinfo=timezone.utc)
                    iso_pub_date = dt.isoformat()
                    dt_pub = dt
                else:
                    dt_pub = datetime.now(timezone.utc)
                    iso_pub_date = dt_pub.isoformat()
            except:
                dt_pub = datetime.now(timezone.utc)
                iso_pub_date = dt_pub.isoformat()
                
            retrieved_dt = datetime.now(timezone.utc)
            delta = (retrieved_dt - dt_pub).total_seconds()
            
            # Point-in-Time Classification
            if delta < 0:
                # Weird future timestamp
                availability_type = "UNKNOWN"
                available_at = retrieved_dt.isoformat()
            elif delta <= 3600:
                # Fetched within an hour of publication -> We are running live
                availability_type = "HISTORICAL_VERIFIED"
                available_at = retrieved_dt.isoformat()
            else:
                # We are fetching old news today
                availability_type = "CURRENTLY_RETRIEVED_HISTORICAL"
                # To be absolutely unassailable, this is only available to our system NOW
                available_at = retrieved_dt.isoformat()

            for sym in matched_symbols:
                # Add to Event Radar
                added = event_radar.add_event(
                    symbol=sym,
                    event_type="public_news",
                    source="Yahoo Finance RSS",
                    source_url=link,
                    headline=title,
                    published_at=iso_pub_date,
                    credibility=0.85,
                    is_simulated=False
                )
                if added:
                    event_radar.update_event(added["event_id"], {
                        "available_at": available_at,
                        "availability_type": availability_type
                    })
                    new_events += 1
                    
        print(f"[RSS Ingestion] Successfully ingested {new_events} new public events.")
    except Exception as e:
        print(f"[RSS Ingestion] Error during ingestion: {e}")

if __name__ == "__main__":
    asyncio.run(ingest_public_news())
