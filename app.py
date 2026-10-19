import io
import json
import os
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import requests
from flask import Flask, jsonify, render_template, request
from pypdf import PdfReader

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 3 * 1024 * 1024
DB = os.environ.get('ATS_DB', str(Path(__file__).parent / 'data' / 'ats.sqlite3'))
lock = threading.Lock()
DEFAULT = dict(name='Samya', linkedin='https://www.linkedin.com/in/samya-samanta/', role='', location='', count=5, days=15, hour='09:00', timezone='Etc/GMT+5', enabled=False, threshold=70)
SKILLS = {'python','java','javascript','typescript','react','angular','vue','node','sql','postgresql','mysql','mongodb','redis','aws','azure','gcp','docker','kubernetes','terraform','linux','git','html','css','django','flask','fastapi','spring','golang','rust','c++','c#','excel','tableau','power bi','pandas','numpy','pytorch','tensorflow','machine learning','data analysis','project management','agile','scrum','figma','sales','marketing','accounting','customer service','communication','leadership','testing','graphql','rest','api','ci/cd'}

def connect():
    Path(DB).parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(DB, timeout=20)
    c.execute('CREATE TABLE IF NOT EXISTS state (key TEXT PRIMARY KEY, value TEXT NOT NULL)')
    return c

def get(key, default=None):
    with connect() as c:
        row = c.execute('SELECT value FROM state WHERE key=?', (key,)).fetchone()
    return json.loads(row[0]) if row else default

def put(key, value):
    with connect() as c:
        c.execute('INSERT OR REPLACE INTO state VALUES (?, ?)', (key, json.dumps(value)))

def skills(text):
    text = text.lower()
    return {s for s in SKILLS if re.search(r'(?<!\w)' + re.escape(s) + r'(?!\w)', text)}

def match(cv, description):
    have, need = skills(cv), skills(description)
    overlap = sorted(have & need)
    missing = sorted(need - have)
    return dict(score=round(100 * len(overlap) / len(need)) if need else 0, matched=overlap, missing=missing, recognized=len(need))

def fetch_jobs():
    r = requests.get('https://remotive.com/api/remote-jobs', timeout=30, headers={'User-Agent':'ATS-Matchmaker/1.0'})
    r.raise_for_status()
    return r.json()['jobs']

def rank_jobs(cv, prefs, jobs, now=None):
    now = now or datetime.now(timezone.utc)
    ranked = []
    for job in jobs:
        try:
            posted = datetime.fromisoformat(job['publication_date'].replace('Z','+00:00'))
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            if not now - timedelta(days=prefs['days']) <= posted <= now:
                continue
            title = job.get('title','')
            if prefs['role'] and not all(t in title.lower() for t in prefs['role'].lower().split()):
                continue
            location = job.get('candidate_required_location','Worldwide')
            if prefs['location'] and prefs['location'].lower() not in location.lower() and location.lower() not in ('worldwide','anywhere'):
                continue
            detail = re.sub('<[^>]+>', ' ', job.get('description',''))
            result = match(cv, title + ' ' + detail)
            if result['score'] < prefs['threshold'] or not result['matched']:
                continue
            url = job.get('url','')
            if not url.startswith('https://remotive.com/'):
                continue
            ranked.append(dict(id=str(job['id']), title=title, company=job.get('company_name',''), location=location, date=posted.isoformat(), url=url, salary=job.get('salary',''), **result))
        except (ValueError, KeyError, TypeError):
            continue
    return sorted(ranked, key=lambda j:(j['score'],j['date']), reverse=True)[:prefs['count']]

def run_search():
    if not lock.acquire(blocking=False):
        raise ValueError('A search is already running. Please wait.')
    try:
        cv = get('cv','')
        if not cv:
            raise ValueError('Upload your CV before searching.')
        prefs = get('prefs', DEFAULT)
        cache = get('source_cache', {})
        if time.time() - cache.get('at',0) < 900:
            jobs = cache['jobs']
        else:
            jobs = fetch_jobs()
            put('source_cache', dict(at=time.time(), jobs=jobs))
        result = dict(jobs=rank_jobs(cv,prefs,jobs), at=datetime.now(timezone.utc).isoformat(), error=None)
        put('result', result)
        return result
    finally:
        lock.release()

def schedule_tick(now=None):
    p = get('prefs', DEFAULT)
    now = (now or datetime.now(timezone.utc)).astimezone(ZoneInfo(p['timezone']))
    day = now.date().isoformat()
    if p['enabled'] and get('cv') and now.strftime('%H:%M') >= p['hour'] and get('last_scheduled_day') != day:
        # One automatic attempt per local day; failures remain visible for manual retry.
        put('last_scheduled_day', day)
        try:
            run_search()
            put('schedule_error', None)
        except Exception:
            put('schedule_error', 'Scheduled search failed. Check connectivity and use Run search to retry.')


def scheduler():
    while True:
        try:
            schedule_tick()
        except Exception:
            app.logger.exception('Scheduler failed')
        time.sleep(30)

@app.before_request
def local_mutations_only():
    if request.is_json and not isinstance(request.get_json(silent=True), dict):
        return jsonify(error='Expected a JSON object.'), 400
    if request.method in ('POST','DELETE'):
        origin = request.headers.get('Origin')
        if origin and origin != request.host_url.rstrip('/'):
            return jsonify(error='Cross-origin writes are not allowed.'), 403

@app.get('/')
def index():
    return render_template('index.html')

@app.get('/api/state')
def state():
    return jsonify(prefs=get('prefs',DEFAULT), cv=get('cv_meta'), result=get('result'), schedule_error=get('schedule_error'))

@app.post('/api/settings')
def settings():
    data = request.get_json() or {}
    p = {**DEFAULT, **{k:v for k,v in data.items() if k in DEFAULT}}
    try:
        for field, low, high in [('count',1,20),('days',1,60),('threshold',1,100)]:
            p[field] = int(p[field])
            if not low <= p[field] <= high:
                raise ValueError('Invalid '+field)
        if not re.fullmatch(r'(?:[01]\d|2[0-3]):[0-5]\d',p['hour']):
            raise ValueError('Invalid time')
        ZoneInfo(p['timezone'])
        if not isinstance(p['enabled'],bool) or any(not isinstance(p[k],str) or len(p[k])>300 for k in ['name','linkedin','role','location']):
            raise ValueError('Invalid settings')
        if p['enabled'] and not get('cv'):
            raise ValueError('Upload your CV before enabling the agent.')
    except (ValueError, TypeError, ZoneInfoNotFoundError) as e:
        return jsonify(error=str(e)),400
    put('prefs', p)
    return jsonify(prefs=p)

@app.post('/api/cv')
def upload():
    f = request.files.get('cv')
    if not f:
        return jsonify(error='Choose a PDF or TXT file.'),400
    try:
        raw = f.read()
        if f.filename.lower().endswith('.pdf'):
            reader = PdfReader(io.BytesIO(raw))
            if len(reader.pages)>30:
                raise ValueError('Please upload a CV with 30 pages or fewer.')
            text = '\n'.join(page.extract_text() or '' for page in reader.pages)
        elif f.filename.lower().endswith('.txt'):
            text = raw.decode('utf-8')
        else:
            raise ValueError('Supported formats: PDF and UTF-8 TXT.')
        if len(text.strip())<40:
            raise ValueError('Not enough readable text. Scanned PDFs need OCR first.')
        if len(text)>150000:
            raise ValueError('CV text is too long.')
    except Exception as e:
        return jsonify(error=str(e) if isinstance(e,ValueError) else 'Could not read this file. Try a text-based PDF or TXT.'),400
    meta = dict(filename=Path(f.filename).name, skills=sorted(skills(text)))
    put('cv',text)
    put('cv_meta',meta)
    put('result',None)
    return jsonify(cv=meta)

@app.delete('/api/cv')
def delete_cv():
    with connect() as c:
        c.execute("DELETE FROM state WHERE key IN ('cv','cv_meta','result')")
    p=get('prefs',DEFAULT).copy()
    p['enabled']=False
    put('prefs',p)
    return jsonify(ok=True)

@app.post('/api/search')
def search():
    try:
        return jsonify(run_search())
    except ValueError as e:
        return jsonify(error=str(e)),400
    except (requests.RequestException, KeyError, TypeError):
        return jsonify(error='Job source is unavailable. Your previous results are preserved. Try again later.'),502

@app.post('/api/analyze')
def analyze():
    cv=get('cv','')
    jd=(request.get_json() or {}).get('jd','')
    if not cv or not isinstance(jd,str) or len(jd.strip())<40:
        return jsonify(error='Upload your CV and paste a job description of at least 40 characters.'),400
    return jsonify(match(cv,jd[:100000]))

@app.errorhandler(413)
def too_large(e):
    return jsonify(error='File too large. Maximum upload size is 3 MB.'),413

if __name__=='__main__':
    threading.Thread(target=scheduler, daemon=True).start()
    app.run(host='127.0.0.1',port=int(os.environ.get('PORT',5000)),debug=False)
