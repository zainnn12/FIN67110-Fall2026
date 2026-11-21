#!/usr/bin/env python3
"""Fixed-rule hit-rate report. It never mutates the production factor file."""
import argparse, json
from datetime import datetime
from pathlib import Path
import hashlib
from zoneinfo import ZoneInfo
ROOT=Path(__file__).resolve().parent
DEFAULT_REGISTRY=ROOT/'lab06_runs/SEEKER_2026-11-20_22-29-06-302032/registry.json'
DEFAULT_OUT=ROOT/'runs/factor_check'
PLAN={
 'feature':'Three Musketeers factor-check',
 'factor_file':'skills/spinoff-seeker/references/factors.json',
 'entry_day':'first regular closing price after distribution',
 'holding_period':'20 trading days after entry close',
 'comparison_benchmark':'SPY regular close over the same dates; no benchmark data is substituted or estimated',
 'sample_rule':'Only distributions after preregistration time can enter this prospective comparison; all three factor inputs must be available before entry.',
 'outcome_rule':'Compare each eligible name’s 20-trading-day price return with SPY return over the same close-to-close interval; report hit only when the frozen weighted score predicts a positive excess return.',
 'weights_percent':[35,40,25],
 'limitations':['No future post-preregistration distribution has a complete 20-trading-day outcome in saved evidence.','No WRDS/CRSP dataset is available.','No Financial Datasets benchmark series is substituted for WRDS/CRSP.','The available historical Lab 06 returns were observed before this preregistration and are excluded.'],
}
def save_plan(path):
 from datetime import datetime
 from zoneinfo import ZoneInfo
 factor_file=ROOT/PLAN['factor_file']; factor_data=json.loads(factor_file.read_text())
 plan={**PLAN,'preregistered_at':datetime.now(ZoneInfo('America/New_York')).isoformat(timespec='seconds'),'factors_sha256':hashlib.sha256(factor_file.read_bytes()).hexdigest(),'factor_definitions':factor_data['factors']}
 path=Path(path); path.parent.mkdir(parents=True,exist_ok=True); path.write_text(json.dumps(plan,indent=2)+'\n'); return path
def render_table(comparisons):
 lines=['| Sample | Ticker | Frozen score | Spinoff return | Benchmark return | Hit |','|---:|---|---:|---:|---:|---|']
 for row in comparisons: lines.append('| {sample} | {ticker} | {score} | {return_value} | {benchmark_return} | {hit} |'.format(**row))
 if not comparisons: lines.append('| 0 | not known | not computed | not computed | not computed | not applicable |')
 lines.extend(['','Comparisons: **0**. Hit rate: **not computed (insufficient prospective sample)**. No factor validation is claimed.'])
 return '\n'.join(lines)+'\n'
def main():
 p=argparse.ArgumentParser(); sp=p.add_subparsers(dest='command',required=True)
 a=sp.add_parser('preregister');a.add_argument('--output',type=Path,default=DEFAULT_OUT/'factor_preregistration.json')
 b=sp.add_parser('hit-rate');b.add_argument('--comparisons',type=Path,default=DEFAULT_OUT/'comparisons.json');b.add_argument('--output',type=Path,default=DEFAULT_OUT/'hit_rate_table.md')
 c=sp.add_parser('run');c.add_argument('--registry',type=Path,default=DEFAULT_REGISTRY);c.add_argument('--output',type=Path,default=DEFAULT_OUT)
 args=p.parse_args()
 if args.command=='preregister': print(save_plan(args.output)); return 0
 if args.command=='run':
  # The fixed dataset is empty until a post-preregistration outcome is available.
  args.output.mkdir(parents=True,exist_ok=True); save_plan(args.output/'factor_preregistration.json')
  (args.output/'comparisons.json').write_text('[]\n')
  table=render_table([]);(args.output/'hit_rate_table.md').write_text(table);print(table);return 0
 comparisons=json.loads(args.comparisons.read_text()) if args.comparisons.is_file() else []
 out=args.output;out.parent.mkdir(parents=True,exist_ok=True);out.write_text(render_table(comparisons));print(out);return 0
if __name__=='__main__': raise SystemExit(main())
