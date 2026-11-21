#!/usr/bin/env python3
"""CRSP close-to-close reaction command. Requires authorized WRDS credentials and event CSV."""
import argparse,csv,json,os
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path
from zoneinfo import ZoneInfo
EASTERN=ZoneInfo('America/New_York')

def reaction(last_close,first_close):
    if last_close in (None,0) or first_close is None: return None
    return str((Decimal(str(first_close))/Decimal(str(last_close))-Decimal(1))*Decimal(100))

def select_close_pair(frame,accepted):
    candidates=[]
    for _,row in frame.iterrows():
        d=row['date'].date() if hasattr(row['date'],'date') else row['date']
        price=float(row['prc'])
        # CRSP uses a negative PRC to flag a bid/ask average, not a regular close.
        if price<=0: continue
        close_time=datetime.combine(d,time(16,0),tzinfo=EASTERN)
        candidates.append((close_time,price))
    before=[x for x in candidates if x[0] < accepted]
    after=[x for x in candidates if x[0] > accepted]
    return (before[-1][1] if before else None,after[0][1] if after else None)

def run(events_path:Path,output_path:Path,connection=None):
    username=os.getenv('WRDS_USERNAME','').strip(); password=os.getenv('WRDS_PASSWORD','').strip()
    if connection is None and not (username and password):
        result={'status':'PENDING WRDS LOGIN — no authorized credentials available.','provider':'WRDS / CRSP','substitution':'none'}
        output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(result,indent=2)+'\n');return result
    if connection is None:
        import wrds
        connection=wrds.Connection(wrds_username=username)
    rows=[]
    with events_path.open(newline='',encoding='utf-8') as f:
      for event in csv.DictReader(f):
        accepted=datetime.fromisoformat(event['accepted_at'])
        # Dataset-specific CRSP table and date are queried only after WRDS authentication.
        sql='''SELECT date, prc, shrout FROM crsp.dsf WHERE permno = %(permno)s AND date BETWEEN %(start)s AND %(end)s ORDER BY date'''
        frame=connection.raw_sql(sql,params={'permno':int(event['permno']),'start':event['start_date'],'end':event['end_date']})
        prior,first=select_close_pair(frame,accepted)
        rows.append({'ticker':event['ticker'],'accession':event['accession'],'accepted_at':accepted.isoformat(),'last_close_before':prior,'first_close_after':first,'reaction_percent':reaction(prior,first)})
    out={'status':'complete','provider':'WRDS / CRSP','rows':rows}
    output_path.parent.mkdir(parents=True,exist_ok=True);output_path.write_text(json.dumps(out,indent=2)+'\n');return out

def main():
 p=argparse.ArgumentParser();p.add_argument('--events',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args(); print(json.dumps(run(a.events,a.output),indent=2));
if __name__=='__main__': main()
