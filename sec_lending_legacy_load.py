# Loads hermesf_sl_legacy in monthly chunks from sec_lending_clean_query_legacy.txt.
# Rerunnable, months that already have rows in the table are skipped.
# Run from the repo folder in a terminal:  python sec_lending_legacy_load.py
# Keep the laptop awake, the Impala session dies when the connection drops.

import datetime as dt
import time
import pyodbc

DB = 'xlab_ecb_prj_sftds_cb_common'
TABLE = f'{DB}.hermesf_sl_legacy'
FIRST = dt.date(2021, 1, 1)
LAST = dt.date(2026, 5, 31)
LOG = 'hermesf_sl_legacy_load.log'
FULL_RANGE = "BETWEEN '2021-01-01' AND '2026-05-31'"

sql = open('sec_lending_clean_query_legacy.txt').read()
body = sql[sql.index('AS\nSELECT') + 3:].rstrip().rstrip(';')   # the SELECT of the cleaning query
assert body.count(FULL_RANGE) == 1

cnxn = pyodbc.connect('DSN=Hermes_DSN', autocommit=True)
cursor = cnxn.cursor()

# monthly chunks
months = []
d = FIRST
while d <= LAST:
    nxt = (d.replace(day=1) + dt.timedelta(days=32)).replace(day=1)
    months.append((d, min(nxt - dt.timedelta(days=1), LAST)))
    d = nxt

# months already in the table
cursor.execute(f"SHOW TABLES IN {DB} LIKE 'hermesf_sl_legacy'")
exists = cursor.fetchone() is not None
done = set()
if exists:
    cursor.execute(f"SELECT SUBSTR(CAST(reference_period AS STRING), 1, 7) AS ym, COUNT(*) AS n FROM {TABLE} GROUP BY 1")
    done = {row[0] for row in cursor.fetchall()}
    print(f'{len(done)} months already loaded')

failed = []
for start, end in months:
    ym = start.strftime('%Y-%m')
    if ym in done:
        continue
    chunk = body.replace(FULL_RANGE, f"BETWEEN '{start}' AND '{end}'")
    if exists:
        stmt = f'INSERT INTO {TABLE}\n' + chunk
    else:
        stmt = (f'CREATE EXTERNAL TABLE {TABLE}\n'
                "STORED AS PARQUET TBLPROPERTIES ('external.table.purge'='true')\nAS\n" + chunk)
    t0 = time.time()
    try:
        cursor.execute(stmt)
        exists = True
        msg = f'{ym} done in {(time.time() - t0) / 60:.1f} min'
    except Exception as e:
        failed.append(ym)
        msg = f'{ym} FAILED after {(time.time() - t0) / 60:.1f} min: {str(e)[:300]}'
        cnxn = pyodbc.connect('DSN=Hermes_DSN', autocommit=True)   # the session may be gone, reconnect
        cursor = cnxn.cursor()
    print(msg, flush=True)
    with open(LOG, 'a') as f:
        f.write(f'{dt.datetime.now():%Y-%m-%d %H:%M} {msg}\n')

print('failed months:', failed or 'none')
