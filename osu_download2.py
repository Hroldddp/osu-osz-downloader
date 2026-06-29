import requests, time, os, json
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed

OUT_DIR = '/home/hroldddp/osu_maps'
os.makedirs(OUT_DIR, exist_ok=True)

HEADERS = {'User-Agent': 'Mozilla/5.0'}
SEARCH_URL = 'https://osu.ppy.sh/beatmapsets/search'
CACHE_FILE = os.path.join(OUT_DIR, 'map_list.json')

def parse_ts(rd):
    try: return int(datetime.fromisoformat(rd.replace('Z','+00:00')).timestamp()*1000)
    except: return None

if os.path.exists(CACHE_FILE):
    with open(CACHE_FILE) as f:
        all_maps = json.load(f)
    print(f'Loaded {len(all_maps)} maps from cache', flush=True)
else:
    START_MS = int(datetime(2011, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    END_MS = int(datetime(2017, 1, 1, tzinfo=timezone.utc).timestamp() * 1000)
    print('Crawling...', flush=True)
    all_maps = []
    cursor = {'approved_date': END_MS, 'id': 999999999}
    while cursor:
        params = {'m': '0', 's': 'ranked', 'limit': 50,
                  'cursor[approved_date]': cursor['approved_date'],
                  'cursor[id]': cursor['id']}
        try:
            r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=15)
            if r.status_code != 200:
                time.sleep(3); continue
            data = r.json()
            maps = data.get('beatmapsets', [])
            cursor = data.get('cursor')
            for b in maps:
                rd = b.get('ranked_date', '')
                ts = parse_ts(rd)
                if ts is None: continue
                if ts < START_MS: cursor = None; break
                if ts < END_MS:
                    all_maps.append({'id': b['id'], 'plays': b.get('play_count', 0)})
            if not cursor: break
            time.sleep(0.1)
        except Exception as e:
            time.sleep(3); continue
    with open(CACHE_FILE, 'w') as f:
        json.dump(all_maps, f)
    print(f'Found {len(all_maps)} maps', flush=True)

all_maps.sort(key=lambda x: x['plays'], reverse=True)
to_download = [m for m in all_maps[:2000] if not os.path.exists(os.path.join(OUT_DIR, f'{m["id"]}.osz'))]
print(f'Need to download {len(to_download)} maps', flush=True)

extra = [1058213, 440392, 575638, 632912, 1613113, 1889701, 2027467, 2205700]
for eid in extra:
    if eid not in {m['id'] for m in to_download} and not os.path.exists(os.path.join(OUT_DIR, f'{eid}.osz')):
        to_download.append({'id': eid, 'plays': 99999999})

mirrors = [
    'https://api.nerinyan.moe/d/{}',
    'https://beatconnect.io/b/{}/',
]

def dl_one(m):
    sid = m['id']
    fpath = os.path.join(OUT_DIR, f'{sid}.osz')
    if os.path.exists(fpath) and os.path.getsize(fpath) > 0:
        return None
    for mirror_tpl in mirrors:
        url = mirror_tpl.format(sid)
        try:
            r = requests.get(url, stream=True, timeout=60, headers=HEADERS)
            if r.status_code == 200:
                with open(fpath, 'wb') as f:
                    for chunk in r.iter_content(8192):
                        if chunk: f.write(chunk)
                return sid
        except:
            continue
    return None

print('Downloading...', flush=True)
done = 0
with ThreadPoolExecutor(max_workers=3) as ex:
    futures = {ex.submit(dl_one, m): m for m in to_download}
    for f in as_completed(futures):
        r = f.result()
        if r:
            done += 1
            if done % 20 == 0:
                print(f'  {done}/{len(to_download)}', flush=True)

total = len([f for f in os.listdir(OUT_DIR) if f.endswith('.osz')])
print(f'Done! {total} maps in {OUT_DIR}', flush=True)
