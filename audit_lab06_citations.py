#!/usr/bin/env python3
"""Check that every cited fact quote exists in saved SEC filing evidence."""
import argparse,json,re
from pathlib import Path
from bs4 import BeautifulSoup

def norm(text): return re.sub(r'\s+',' ',text).strip().casefold()
def audit(run:Path):
    payload=json.loads((run/'registry.json').read_text()); rows=[]
    for record in payload.get('records',[]):
      if record.get('classification')!='spinoff': continue
      for fact_name,fact in (record.get('facts') or {}).items():
        source=(fact or {}).get('source') if isinstance(fact,dict) else None
        if not isinstance(source,dict): continue
        accession=str(source.get('accession','')); compact=accession.replace('-','')
        paths=set(run.joinpath('raw/sec').rglob(f'*{accession}*'))|set(run.joinpath('raw/sec').rglob(f'*{compact}*'))
        paths=[p for p in paths if p.is_file()]
        quote=norm(str(source.get('quote',''))); matched=[]
        for path in paths:
          raw=path.read_text(errors='replace')
          text=BeautifulSoup(raw,'html.parser').get_text(' ') if path.suffix.lower() in {'.html','.htm'} else raw
          if quote and quote in norm(text): matched.append(str(path.relative_to(run)))
        rows.append({'company':record.get('company'),'ticker':record.get('ticker'),'fact':fact_name,'accession':accession,'quote_found':bool(matched),'saved_documents':matched})
    return {'run':str(run),'citation_count':len(rows),'quote_matches':sum(r['quote_found'] for r in rows),'all_quotes_supported':bool(rows) and all(r['quote_found'] for r in rows),'citations':rows}
def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();out=audit(a.run);a.output.parent.mkdir(parents=True,exist_ok=True);a.output.write_text(json.dumps(out,indent=2)+'\n');print(f"Cited fact quotes: {out['quote_matches']}/{out['citation_count']} supported")
if __name__=='__main__': main()
