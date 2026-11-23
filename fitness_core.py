"""Local storage and Ollama integration for the single-user fitness app."""
import base64
import io
import json
import math
import os
from pathlib import Path
import sqlite3
import urllib.error
import urllib.request
from PIL import Image, ImageOps

DB = Path(os.environ.get('FITNESS_DB', Path(__file__).parent / 'data/fitness.sqlite3'))

DEFAULT_OWNER = 'main'  # Records saved before profiles existed belong to the first profile.


def connect():
    DB.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB)
    db.execute('CREATE TABLE IF NOT EXISTS records (id INTEGER PRIMARY KEY, kind TEXT NOT NULL, day TEXT NOT NULL, payload TEXT NOT NULL)')
    if 'owner' not in {row[1] for row in db.execute('PRAGMA table_info(records)')}:
        db.execute('ALTER TABLE records ADD COLUMN owner TEXT')
    return db

def save(kind, day, payload, owner=None):
    with connect() as db:
        return db.execute('INSERT INTO records(kind,day,payload,owner) VALUES (?,?,?,?)', (kind, str(day), json.dumps(payload, ensure_ascii=False), owner)).lastrowid

def records(kind, owner=None):
    """Return records of one kind; with ``owner``, only those of that profile."""
    query = 'SELECT id,day,payload FROM records WHERE kind=?'
    params = [kind]
    if owner is not None:
        query += ' AND COALESCE(owner,?)=?'
        params += [DEFAULT_OWNER, owner]
    with connect() as db:
        return [dict(id=r[0], day=r[1], **json.loads(r[2])) for r in db.execute(query + ' ORDER BY day,id', params)]

def profiles():
    """Latest version of every profile as {owner: profile}, in creation order."""
    result = {}
    with connect() as db:
        rows = db.execute("SELECT COALESCE(owner,?),payload FROM records WHERE kind='profile' ORDER BY id", (DEFAULT_OWNER,))
        for owner, payload in rows:
            result[owner] = json.loads(payload)
    return result

def delete(record_id):
    with connect() as db:
        db.execute('DELETE FROM records WHERE id=?', (record_id,))

def delete_owner(owner):
    """Remove a profile together with all of its data."""
    with connect() as db:
        db.execute('DELETE FROM records WHERE COALESCE(owner,?)=?', (DEFAULT_OWNER, owner))

RECOMMENDED_VISION_MODEL = 'llama3.2-vision:11b'


def _installed():
    with urllib.request.urlopen('http://localhost:11434/api/tags', timeout=3) as response:
        return json.load(response)['models']

def models():
    return [m['name'] for m in _installed()
            if 'completion' in m.get('capabilities', []) or
            (not m.get('capabilities') and 'embed' not in m['name'].lower())]

def vision_models():
    """Installed models that can read images (Ollama reports the 'vision' capability)."""
    return [m['name'] for m in _installed() if 'vision' in m.get('capabilities', [])]

def _open(request):
    """Open an Ollama request and turn HTTP errors into Ollama's own readable message."""
    try:
        return urllib.request.urlopen(request, timeout=180)
    except urllib.error.HTTPError as exc:
        try:
            message = json.loads(exc.read()).get('error') or str(exc)
        except Exception:
            message = str(exc)
        if exc.code == 404 and 'not found' in message:
            message += f'. Install it with: ollama pull {json.loads(request.data).get("model")}'
        raise RuntimeError(message) from None

def ask(model, prompt, image=None, structured=False):
    message = {'role':'user', 'content':prompt}
    if image:
        with Image.open(io.BytesIO(image)) as picture:
            picture = ImageOps.exif_transpose(picture).convert('RGB')
            picture.thumbnail((1280, 1280))
            buffer = io.BytesIO()
            picture.save(buffer, format='JPEG', quality=85)
            message['images'] = [base64.b64encode(buffer.getvalue()).decode()]
    body = {'model': model, 'stream': False, 'messages': [
        {'role':'system','content':'You are a fitness coach. Reply in English. Do not diagnose or guarantee results. Consider allergies, limitations, recovery, and realistic goals. Recommend professional medical advice for symptoms or medical concerns. Avoid extreme diets and clearly state uncertainty.'}, message], 'options': {'temperature':0.3}}
    if structured:
        body['format'] = 'json'
    request = urllib.request.Request('http://localhost:11434/api/chat', data=json.dumps(body).encode(), headers={'Content-Type':'application/json'})
    with _open(request) as response:
        answer = json.load(response)['message']['content']
    return json.loads(answer) if structured else answer


COACH_SYSTEM = (
    'You are a fitness coach. Reply in English, directly and concisely. '
    'Normally use no more than 150 words; use a compact table for training plans. '
    'Do not diagnose or guarantee results. Consider allergies, limitations, recovery, '
    'and realistic goals. Avoid extreme diets and clearly state uncertainty. '
    'Recommend professional medical advice for medical concerns.'
)


def coach_messages(profile, history, question):
    """Preserve chat roles and cap context without cutting individual messages."""
    messages = [{'role': 'system', 'content': COACH_SYSTEM + '\nProfile: ' +
                 json.dumps(profile, ensure_ascii=False)}]
    recent = []
    remaining = max(0, 10000 - len(messages[0]['content']) - len(question))
    for role, content in reversed(history[-8:]):
        if role not in ('user', 'assistant'):
            continue
        if len(content) > remaining:
            break
        recent.append({'role': role, 'content': content})
        remaining -= len(content)
    recent.reverse()
    # Never start the retained conversation with an orphan assistant response.
    while recent and recent[0]['role'] != 'user':
        recent.pop(0)
    return messages + recent + [{'role': 'user', 'content': question}]


def stream_coach(model, profile, history, question, *, plan=False):
    """Yield Ollama content as it arrives instead of buffering the whole reply."""
    body = {
        'model': model, 'stream': True, 'keep_alive': '30m',
        'messages': coach_messages(profile, history, question),
        'options': {'temperature': 0.3, 'num_predict': 1800 if plan else 512, 'num_ctx': 4096},
    }
    if plan:
        body['messages'][0]['content'] += '\nFor this plan, prioritize completeness over the word limit and use compact tables.'
    request = urllib.request.Request(
        'http://localhost:11434/api/chat', data=json.dumps(body).encode(),
        headers={'Content-Type': 'application/json'})
    completed = False
    received = False
    with _open(request) as response:
        for line in response:
            if not line.strip():
                continue
            chunk = json.loads(line)
            if chunk.get('error'):
                raise RuntimeError(chunk['error'])
            content = chunk.get('message', {}).get('content', '')
            if content:
                received = True
                yield content
            if chunk.get('done'):
                completed = True
                if chunk.get('done_reason') == 'length':
                    yield '\n\n*Response limit reached. Ask for specific details to continue.*'
                break
    if not completed or not received:
        raise RuntimeError('The response was interrupted or empty. Please try again.')

def validate_meal(data):
    if not isinstance(data, dict) or data.get('is_food') is not True:
        raise ValueError('No meal was detected reliably. Please use a clearer photo.')
    result = {'name': str(data.get('name', 'Meal'))[:200]}
    for key in ('kcal','protein','carbs','fat'):
        value = data.get(key)
        if isinstance(value, bool) or not isinstance(value, (float,int)) or not math.isfinite(value) or not 0 <= value <= 10000:
            raise ValueError('The model returned incomplete nutrition values. Please analyze the photo again.')
        result[key] = float(value)
    result['assumptions'] = str(data.get('assumptions', 'Portion size and ingredients are estimated.'))
    return result
