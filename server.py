#!/usr/bin/env python3
"""
Molly's Fitness Coaching — CRM & Email Automation
Flask backend · Railway-deployable
"""

import json, os, uuid, smtplib, subprocess
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, jsonify, request, send_from_directory

# ── Auto-load .env ─────────────────────────────────────────────────────────────
_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
if os.path.exists(_env):
    with open(_env) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip())

# ── Config ─────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
DATA_DIR    = os.path.join(BASE_DIR, 'data')
PUBLIC_DIR  = os.path.join(BASE_DIR, 'public')
LEADS_FILE  = os.path.join(DATA_DIR, 'fitness_leads.json')
TASKS_FILE  = os.path.join(DATA_DIR, 'tasks.json')
CONFIG_FILE = os.path.join(DATA_DIR, 'config.json')
PORT        = int(os.environ.get('PORT', 3001))

GMAIL_USER  = os.environ.get('GMAIL_USER', 'mollylmangan@gmail.com')
GMAIL_PASS  = os.environ.get('GMAIL_APP_PASSWORD', '').replace(' ', '')
ADMIN_KEY   = os.environ.get('ADMIN_KEY', '')

os.makedirs(DATA_DIR, exist_ok=True)

def _init(path, default):
    if not os.path.exists(path):
        with open(path, 'w') as f:
            json.dump(default, f, indent=2)

_init(LEADS_FILE, [])
_init(TASKS_FILE, [])
_init(CONFIG_FILE, {
    'coachName': 'Molly Mangan',
    'instagram': '@mollylmangan',
    'guideName': 'How to Build Glutes That Actually Grow',
    'clientGoal': 20,
    'updatedAt': datetime.utcnow().isoformat()
})

# ── Helpers ────────────────────────────────────────────────────────────────────
def read_json(path):
    with open(path) as f: return json.load(f)

def write_json(path, data):
    with open(path, 'w') as f: json.dump(data, f, indent=2)

def now_iso(): return datetime.utcnow().isoformat()

def get_first_name(full_name):
    if not full_name: return 'there'
    first = full_name.strip().split()[0].title()
    return first if len(first) >= 2 and first.replace("'", '').isalpha() else 'there'

# ── Gmail ──────────────────────────────────────────────────────────────────────
def send_email(to_addr, subject, body):
    if not GMAIL_PASS:
        raise ValueError('GMAIL_APP_PASSWORD not configured')
    msg = MIMEMultipart()
    msg['From']    = f'"Molly Mangan" <{GMAIL_USER}>'
    msg['To']      = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP('smtp.gmail.com', 587, timeout=15) as s:
        s.ehlo(); s.starttls(); s.ehlo()
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, [to_addr], msg.as_string())

# ── Email sequence templates ───────────────────────────────────────────────────
SIG = '\nMolly\n@mollylmangan'
SEQUENCE_DAYS = [0, 3, 6, 9, 13, 17]

def _email(step, first):
    if step == 0:
        return {
            'subject': 'the thing nobody tells you after downloading a glute guide 👀',
            'body': f"""Hey {first},

Thanks for grabbing my "How to Build Glutes That Actually Grow" guide!

Quick heads up — most people read it, get excited, then go back to their usual routine and wonder why nothing changes.

The guide gives you the *what*. This email gives you the *why*.

The #1 reason glutes don't grow isn't the exercises. It's the mind-muscle connection. Your brain literally has to learn to recruit your glutes before they'll respond to training — otherwise your quads and hamstrings steal all the work.

Here's the one thing to do THIS WEEK:

Before every glute exercise, do 15 slow bodyweight hip thrusts with a 3-second squeeze at the top. No weight. Just activation. This wakes up your glutes so when you load the movement, they actually fire.

Try it and DM me how it felt — I'm always on Instagram: @mollylmangan{SIG}"""
        }
    if step == 1:
        return {
            'subject': '6.5 inches off her waist. 30 days. (Vanessa\'s story)',
            'body': f"""Hey {first},

I need to share something because it honestly still gets me every time.

My client Vanessa came to me last month. She'd worked out on and off for years but never saw the shape she was going for. She was close to giving up.

In her first month working with me:

→ Waist went from 38 inches down to 31.5 inches
→ Hips gained 1 inch
→ She's lifting weights she never thought she could touch

6.5 inches. One month. Real food, real training, no gimmicks.

And my client Andrea had never worked out a day in her life before we started. She's now getting stronger every single week — and the cravings she used to battle every night? Completely gone.

These results don't come from a harder workout. They come from a plan that's actually built for your body.

If you're curious what that could look like for you, just hit reply. I read every email personally.{SIG}"""
        }
    if step == 2:
        return {
            'subject': 'the real reason your glutes aren\'t growing',
            'body': f"""Hey {first},

I'm going to be honest about something most fitness coaches won't say:

Most glute programs don't work — not because the exercises are wrong, but because they're built for nobody in particular.

Here are the five mistakes I see constantly:

❌ Training glutes every day (they need 48hrs to recover and grow)
❌ Not eating enough protein (muscle literally cannot build without it)
❌ Skipping hip hinge movements — deadlifts, RDLs — the #1 driver of glute growth
❌ Too much cardio cancelling out the muscle you're trying to build
❌ No progressive overload — doing the same weight every week

The fix isn't more effort. It's a smarter plan built around how your body actually works.

That's what I do with my 1:1 clients. I look at what you're doing, what you're eating, and what your goal actually is — then build a program around you specifically.

My Custom Fitness Plan is $150/month: a fully custom training program, nutrition guidance, and monthly check-ins.

Reply "CUSTOM" and I'll send you the details.{SIG}"""
        }
    if step == 3:
        return {
            'subject': 'here\'s exactly what working with me looks like',
            'body': f"""Hey {first},

A few days ago I shared Vanessa's results — 6.5 inches off her waist and 1 inch added to her hips in one month.

So let me be completely direct about what I offer:

──────────────────────────
💪 CUSTOM FITNESS PLAN — $150/month
──────────────────────────
→ Fully custom training program for your goals and schedule
→ Nutrition advice (real food, not a restrictive diet)
→ Monthly check-ins to adjust as you progress
→ Access to message me with questions

──────────────────────────
🥇 PREMIUM 1:1 COACHING — $300/month
──────────────────────────
→ Everything above, plus:
→ Weekly check-ins (not monthly)
→ Video form reviews
→ Full nutrition coaching
→ Priority access to me throughout the week

Both options have limited spots — I only take on clients I can actually give real attention to.

Reply with your goal and I'll tell you which option makes the most sense for you. No pressure, just an honest conversation.{SIG}"""
        }
    if step == 4:
        today = datetime.utcnow()
        summer = datetime(today.year, 6, 21)
        weeks  = max(1, round((summer - today).days / 7))
        return {
            'subject': f'summer is {weeks} weeks away. here\'s what I\'d do.',
            'body': f"""Hey {first},

Summer is {weeks} weeks away. I know — where did the time go.

Here's the thing: {weeks} weeks is the perfect window. Focused, consistent work in this window produces real, visible results.

That's why I put together the Summer Cut Program:

──────────────────────────
☀️ SUMMER CUT — $600 flat (8 weeks)
──────────────────────────
→ Custom training plan built for a lean, toned summer look
→ Glute-focused programming (you came here for a reason 😉)
→ Nutrition coaching — real food, no starving yourself
→ Weekly check-ins for all 8 weeks
→ Direct access to me throughout

Vanessa lost 6.5 inches off her waist in her first month. Eight focused weeks with a clear summer goal? That's a completely different body by June.

I'm only taking a small number of clients for this round. Once those spots are filled, that's it until fall.

Reply "SUMMER" and I'll get you started.{SIG}

P.S. If summer timing doesn't work, my $150/mo Custom Fitness Plan is always open."""
        }
    # step == 5
    return {
        'subject': 'last email from me (here\'s where things stand)',
        'body': f"""Hey {first},

This is the last email I'll send you about coaching.

If none of my previous emails landed — totally fine. Timing is everything. No hard feelings at all.

But if you've been reading along and haven't pulled the trigger yet, here's one last clear picture:

☀️  Summer Cut — $600 (8 weeks)
Focused program for a real summer transformation. Limited spots.

💪  Custom Fitness Plan — $150/mo
Fully custom program built for your body. Most accessible way to work with me.

🥇  Premium 1:1 Coaching — $300/mo
Full access, weekly check-ins, nutrition + training.

My clients Vanessa and Andrea are seeing results that genuinely surprise even them. I want that for more people.

If you're ready, just reply with which option interests you and we'll go from there.

If not — genuinely no worries. I'm on Instagram daily (@mollylmangan) and you're always welcome there.

Wishing you the best either way. 🤍{SIG}"""
    }

# ── Sequence engine ────────────────────────────────────────────────────────────
def get_due_step(lead, today_str):
    start = lead.get('sequenceStartDate', '')
    if not start: return -1
    step = lead.get('sequenceStep', 0)
    if step >= len(SEQUENCE_DAYS): return -1
    try:
        d0    = datetime.strptime(start[:10], '%Y-%m-%d')
        today = datetime.strptime(today_str, '%Y-%m-%d')
        if (today - d0).days >= SEQUENCE_DAYS[step]:
            return step
    except ValueError:
        pass
    return -1

def advance_lead(lead_id, step_sent):
    leads = read_json(LEADS_FILE)
    for i, l in enumerate(leads):
        if l['id'] == lead_id:
            next_step = step_sent + 1
            leads[i]['sequenceStep']  = next_step
            leads[i]['lastEmailedAt'] = now_iso()
            leads[i]['emailsSent']    = l.get('emailsSent', []) + [
                {'step': step_sent, 'sentAt': now_iso()}
            ]
            if next_step >= len(SEQUENCE_DAYS):
                leads[i]['status'] = 'sequence_complete'
            write_json(LEADS_FILE, leads)
            return leads[i]
    return None

def do_generate_tasks():
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    leads  = read_json(LEADS_FILE)
    tasks  = read_json(TASKS_FILE)
    exists = {
        (t.get('fitnessLeadId'), t.get('sequenceStep'))
        for t in tasks
        if t.get('fitnessLeadId') and t.get('status') in ('pending', 'approved', 'sent')
    }
    new_tasks = []
    for lead in leads:
        if lead.get('status') != 'active': continue
        step = get_due_step(lead, today_str)
        if step == -1: continue
        if (lead['id'], step) in exists: continue
        first   = get_first_name(lead.get('name', ''))
        content = _email(step, first)
        new_tasks.append({
            'id':            str(uuid.uuid4()),
            'fitnessLeadId': lead['id'],
            'sequenceStep':  step,
            'taskType':      'fitness_sequence',
            'status':        'pending',
            'channel':       'email',
            'subject':       content['subject'],
            'script':        content['body'],
            'recipientEmail': lead.get('email', ''),
            'recipientName':  lead.get('name', ''),
            'scheduledDay':   today_str,
            'createdAt':      now_iso(),
        })
    if new_tasks:
        tasks.extend(new_tasks)
        write_json(TASKS_FILE, tasks)
    return len(new_tasks)

# ── Flask app ──────────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=PUBLIC_DIR)

@app.route('/')
def index():
    return send_from_directory(PUBLIC_DIR, 'index.html')

# ── Stats ──────────────────────────────────────────────────────────────────────
@app.route('/api/stats')
def stats():
    leads  = read_json(LEADS_FILE)
    tasks  = read_json(TASKS_FILE)
    config = read_json(CONFIG_FILE)
    ft     = [t for t in tasks if t.get('taskType') == 'fitness_sequence']
    from collections import Counter
    by_step = Counter(
        l.get('sequenceStep', 0)
        for l in leads if l.get('status') == 'active'
    )
    by_status = Counter(l.get('status') for l in leads)
    converted = by_status.get('converted', 0)
    goal      = config.get('clientGoal', 20)
    return jsonify({
        'totalLeads':      len(leads),
        'active':          by_status.get('active', 0),
        'sequenceComplete': by_status.get('sequence_complete', 0),
        'converted':       converted,
        'clientGoal':      goal,
        'pctToGoal':       round(converted / goal * 100) if goal else 0,
        'tasksPending':    sum(1 for t in ft if t.get('status') == 'pending'),
        'tasksApproved':   sum(1 for t in ft if t.get('status') == 'approved'),
        'tasksSent':       sum(1 for t in ft if t.get('status') == 'sent'),
        'tasksSkipped':    sum(1 for t in ft if t.get('status') == 'skipped'),
        'byStep':          {str(k): v for k, v in by_step.items()},
        'emailConfigured': bool(GMAIL_PASS),
    })

# ── Tasks ──────────────────────────────────────────────────────────────────────
@app.route('/api/tasks')
def get_tasks():
    tasks  = read_json(TASKS_FILE)
    ft     = [t for t in tasks if t.get('taskType') == 'fitness_sequence']
    status = request.args.get('status')
    if status: ft = [t for t in ft if t.get('status') == status]
    ft.sort(key=lambda t: (t.get('sequenceStep', 0), t.get('scheduledDay', '')))
    return jsonify(ft)

@app.route('/api/tasks/<tid>/approve', methods=['POST'])
def approve_task(tid):
    tasks = read_json(TASKS_FILE)
    idx   = next((i for i, t in enumerate(tasks) if t['id'] == tid), None)
    if idx is None: return jsonify({'error': 'Not found'}), 404
    task = tasks[idx]
    if task.get('channel') == 'email' and task.get('recipientEmail') and GMAIL_PASS:
        try:
            send_email(task['recipientEmail'], task.get('subject', ''), task.get('script', ''))
            tasks[idx]['status'] = 'sent'
            tasks[idx]['sentAt'] = now_iso()
            advance_lead(task.get('fitnessLeadId'), task.get('sequenceStep', 0))
        except Exception as e:
            tasks[idx]['status']     = 'approved'
            tasks[idx]['emailError'] = str(e)
            write_json(TASKS_FILE, tasks)
            return jsonify({'error': f'Email failed: {e}', 'task': tasks[idx]}), 500
    else:
        tasks[idx]['status']     = 'approved'
        tasks[idx]['approvedAt'] = now_iso()
    write_json(TASKS_FILE, tasks)
    return jsonify(tasks[idx])

@app.route('/api/tasks/<tid>/skip', methods=['POST'])
def skip_task(tid):
    tasks = read_json(TASKS_FILE)
    for i, t in enumerate(tasks):
        if t['id'] == tid:
            tasks[i]['status']    = 'skipped'
            tasks[i]['skippedAt'] = now_iso()
            write_json(TASKS_FILE, tasks)
            return jsonify(tasks[i])
    return jsonify({'error': 'Not found'}), 404

@app.route('/api/tasks/approve-all', methods=['POST'])
def approve_all():
    """Batch-approve all pending tasks."""
    tasks   = read_json(TASKS_FILE)
    sent    = 0
    errors  = 0
    for i, task in enumerate(tasks):
        if task.get('taskType') != 'fitness_sequence': continue
        if task.get('status') != 'pending': continue
        if task.get('channel') == 'email' and task.get('recipientEmail') and GMAIL_PASS:
            try:
                send_email(task['recipientEmail'], task.get('subject', ''), task.get('script', ''))
                tasks[i]['status'] = 'sent'
                tasks[i]['sentAt'] = now_iso()
                advance_lead(task.get('fitnessLeadId'), task.get('sequenceStep', 0))
                sent += 1
            except Exception:
                errors += 1
        else:
            tasks[i]['status']     = 'approved'
            tasks[i]['approvedAt'] = now_iso()
    write_json(TASKS_FILE, tasks)
    return jsonify({'sent': sent, 'errors': errors})

# ── Generate ───────────────────────────────────────────────────────────────────
@app.route('/api/generate', methods=['POST'])
def generate():
    try:
        n = do_generate_tasks()
        return jsonify({'success': True, 'created': n})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Leads ──────────────────────────────────────────────────────────────────────
@app.route('/api/leads')
def get_leads():
    leads  = read_json(LEADS_FILE)
    status = request.args.get('status')
    search = request.args.get('search', '').lower()
    source = request.args.get('source')
    if status: leads = [l for l in leads if l.get('status') == status]
    if source: leads = [l for l in leads if l.get('source','').lower() == source.lower()]
    if search:
        leads = [l for l in leads if
                 search in (l.get('name') or '').lower() or
                 search in (l.get('email') or '').lower()]
    page  = int(request.args.get('page', 1))
    limit = int(request.args.get('limit', 50))
    total = len(leads)
    start = (page - 1) * limit
    return jsonify({'leads': leads[start:start+limit], 'total': total, 'page': page})

@app.route('/api/leads/<lid>', methods=['PUT'])
def update_lead(lid):
    leads = read_json(LEADS_FILE)
    for i, l in enumerate(leads):
        if l['id'] == lid:
            leads[i] = {**l, **request.json, 'updatedAt': now_iso()}
            write_json(LEADS_FILE, leads)
            return jsonify(leads[i])
    return jsonify({'error': 'Not found'}), 404

# ── Config ─────────────────────────────────────────────────────────────────────
@app.route('/api/config', methods=['GET'])
def get_config(): return jsonify(read_json(CONFIG_FILE))

@app.route('/api/config', methods=['PUT'])
def update_config():
    cfg = {**read_json(CONFIG_FILE), **request.json, 'updatedAt': now_iso()}
    write_json(CONFIG_FILE, cfg)
    return jsonify(cfg)

# ── Admin sync (local → Railway) ───────────────────────────────────────────────
@app.route('/api/admin/sync', methods=['POST'])
def admin_sync():
    key = request.headers.get('X-Admin-Key', '')
    if not ADMIN_KEY or key != ADMIN_KEY:
        return jsonify({'error': 'Unauthorized'}), 401
    data = request.json or {}
    if 'leads' in data: write_json(LEADS_FILE, data['leads'])
    if 'tasks' in data: write_json(TASKS_FILE, data['tasks'])
    return jsonify({'ok': True,
                    'leads': len(data.get('leads', [])),
                    'tasks': len(data.get('tasks', []))})

# ── Run ────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    print(f'\n💪 Molly\'s Fitness CRM → http://localhost:{PORT}')
    print(f'📧 Gmail: {"✅ Ready" if GMAIL_PASS else "⚠️  Add GMAIL_APP_PASSWORD to .env"}')
    print(f'👥 Leads: {len(read_json(LEADS_FILE))} loaded\n')
    app.run(host='0.0.0.0', port=PORT, debug=False)
