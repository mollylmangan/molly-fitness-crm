#!/usr/bin/env python3
"""
Molly's Fitness Coaching - CRM & Email Automation
Flask backend · Railway-deployable
"""

import json, os, uuid, smtplib, subprocess, threading
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
RESEND_KEY  = os.environ.get('RESEND_API_KEY', '')
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

# ── Email (Resend HTTPS API — SMTP blocked on Railway) ─────────────────────────
import urllib.request as _urllib_req

def _send_via_resend(to_addr, subject, body):
    import urllib.error as _urllib_err
    payload = json.dumps({
        'from': 'Molly Mangan <onboarding@resend.dev>',
        'to': [to_addr],
        'subject': subject,
        'text': body,
        'reply_to': GMAIL_USER
    }).encode()
    req = _urllib_req.Request(
        'https://api.resend.com/emails',
        data=payload,
        headers={'Authorization': f'Bearer {RESEND_KEY}', 'Content-Type': 'application/json'},
        method='POST'
    )
    try:
        with _urllib_req.urlopen(req, timeout=15) as r:
            pass
    except _urllib_err.HTTPError as e:
        raise ValueError(f'Resend {e.code}: {e.read().decode()}')

def _send_via_gmail(to_addr, subject, body):
    msg = MIMEMultipart()
    msg['From']    = f'"Molly Mangan" <{GMAIL_USER}>'
    msg['To']      = to_addr
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as s:
        s.ehlo(); s.starttls(); s.ehlo()
        s.login(GMAIL_USER, GMAIL_PASS)
        s.sendmail(GMAIL_USER, [to_addr], msg.as_string())

def send_email(to_addr, subject, body):
    if RESEND_KEY:
        _send_via_resend(to_addr, subject, body)
    elif GMAIL_PASS:
        _send_via_gmail(to_addr, subject, body)
    else:
        raise ValueError('No email credentials configured')

def send_email_batch(messages):
    results = []
    for to_addr, subject, body in messages:
        try:
            send_email(to_addr, subject, body)
            results.append((to_addr, True, None))
        except Exception as e:
            results.append((to_addr, False, str(e)))
    return results

# ── Email sequence templates ───────────────────────────────────────────────────
SIG = '\nMolly'
STAN = 'stan.store/mollylmangan'
SEQUENCE_DAYS = [0, 3, 6, 9, 13, 17]

def _email(step, first):
    if step == 0:
        return {
            'subject': 'quick question about the guide',
            'body': f"""Hey {first},

Thanks for downloading. I hope you have had a chance to look through it.

Two things in the guide that I think most people skim but that matter more than anything else:

The RPE section. The guide explains it but the honest version is this: if you could do 5 more reps when you finish a set, you are not working hard enough for your glutes to grow. Staying 1 to 3 reps from failure is the zone where real growth happens. It is uncomfortable. That is the point.

The progression section. The weight needs to go up over time. Not every session, but consistently over weeks. I see a lot of women who are incredibly consistent and still not making progress simply because they have been lifting the same weight for months. Consistency without progression is maintenance, not growth.

I put a lot of work into this guide and I genuinely want to know if it is landing. Was there anything that clicked right away? Anything confusing, or anything you want me to go deeper on?

Reply and let me know. I read every one.{SIG}"""
        }
    if step == 1:
        return {
            'subject': 'wanted to share this',
            'body': f"""Hey {first},

I have a client named Vanessa. She had been working out on and off for years and was close to giving up because she never saw the shape she was working toward.

In her first month with me her waist went from 38 inches to 31.5 inches and her hips gained an inch. She is now lifting weights she never thought she could.

I also work with Andrea who had never trained a day in her life before we started. She is getting stronger every week and the cravings she used to fight every night are completely gone.

I am not sharing this to impress you. I am sharing it because I think a lot of people are one good plan away from results like that and do not know it.

What has your experience been? Have you tried a structured program before or has it mostly been figuring things out on your own?

Either way, just reply. I am genuinely happy to hear where you are at.{SIG}"""
        }
    if step == 2:
        return {
            'subject': 'the honest reason your glutes are not growing',
            'body': f"""Hey {first},

I see the same five mistakes constantly and I want to be straight with you about them.

Training glutes every day. They need at least 48 hours to recover. Training them every day is one of the fastest ways to stall.

Not enough protein. Muscle cannot build without it. Most people eating a normal diet are well short of what they actually need.

Skipping hip hinge movements. Deadlifts and Romanian deadlifts are the biggest drivers of glute growth and most programs either skip them or bury them at the end when you are already tired.

Too much cardio. Long steady state cardio and muscle building work against each other if you are not eating enough to support both.

No progressive overload. If you are lifting the same weight week after week you are maintaining, not growing.

If you are being consistent and not seeing results it is almost certainly one of these.

I put together custom plans for people who are stuck here. If you want me to take a look at what you are doing and build something that fits your body and schedule, everything is at {STAN}.

And if you want a second opinion on your current routine before committing to anything, just reply with what you are doing. Happy to give you honest feedback.{SIG}"""
        }
    if step == 3:
        return {
            'subject': 'what working with me actually looks like',
            'body': f"""Hey {first},

A few days ago I mentioned Vanessa losing 6.5 inches off her waist in one month. I got a lot of replies asking what that actually involved, so I want to be direct about what I offer.

The Custom Fitness Plan is $150 a month. You get a training program built specifically for your goals and your schedule, nutrition advice that is not a restrictive diet, monthly check-ins to adjust as you go, and the ability to message me with questions.

The Premium 1:1 Coaching is $300 a month. Everything above plus weekly check-ins instead of monthly, video form reviews, full nutrition coaching, and priority access to me during the week.

Both have limited spots because I want to give each person real attention.

If either sounds like a fit you can see the details and sign up at {STAN}.

If you are not sure which one makes sense for your situation, just reply and tell me your goal. I will tell you honestly which is the better fit and why.{SIG}"""
        }
    if step == 4:
        today  = datetime.utcnow()
        summer = datetime(today.year, 6, 21)
        weeks  = max(1, round((summer - today).days / 7))
        return {
            'subject': f'summer is {weeks} weeks away',
            'body': f"""Hey {first},

Summer is {weeks} weeks away. I know that can sound like I am trying to create urgency. I am not. I just think it is useful context.

Eight weeks is a realistic window for a visible change if the plan is right. Not a dramatic transformation, but a real one. Enough to build shape, tighten up, and actually feel good going into summer.

I put together an 8-week summer cut program for exactly that. It is $600 flat. You get a custom training plan built for a leaner, more toned look, glute-focused programming, nutrition coaching, weekly check-ins for all 8 weeks, and direct access to me throughout.

Vanessa's results came in one month. Eight focused weeks with a clear summer goal is a different thing entirely.

I only have a small number of spots because I want to give everyone proper attention. Once they are filled that is it until fall.

If you want in, everything is at {STAN}.

And if summer is not your focus right now, the $150 monthly plan is always open. What matters more to you at the moment, something to work toward for summer or building a longer term habit?{SIG}"""
        }
    # step == 5
    return {
        'subject': 'last one from me',
        'body': f"""Hey {first},

This is the last email I will send you about coaching. I do not want to keep showing up in your inbox if it is not useful.

If none of this has felt like the right fit, no hard feelings at all. Timing is everything.

But if you have been reading along and just have not taken a step yet, here is where things stand.

The Summer Cut is $600 for 8 weeks. It is the focused option if you have a specific goal tied to summer.

The Custom Fitness Plan is $150 a month. It is the most accessible way to work with me on an ongoing basis.

The Premium 1:1 Coaching is $300 a month. It is the most hands-on option with weekly check-ins and full access.

Everything is at {STAN} if any of it feels right.

If not, I post on Instagram every day at @mollylmangan and you are always welcome there.

Thanks for reading along. I genuinely hope whatever you are working toward goes well.{SIG}"""
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
        if t.get('fitnessLeadId') and t.get('status') in ('pending', 'approved', 'sent', 'queued', 'failed')
    }
    new_tasks = []
    for lead in leads:
        if len(new_tasks) >= DAILY_LIMIT: break
        if lead.get('status') != 'active': continue
        step = get_due_step(lead, today_str)
        if step == -1: continue
        if step != 0: continue  # Day 1 emails only — remove this line when ready to send follow-ups
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
            'recipientEmail':  lead.get('email', ''),
            'recipientName':   lead.get('name', ''),
            'recipientSource': lead.get('source', ''),
            'scheduledDay':    today_str,
            'createdAt':       now_iso(),
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
    # Safety net: block if already sent
    if _already_sent(tasks, task.get('fitnessLeadId'), task.get('sequenceStep', 0)):
        tasks[idx]['status'] = 'skipped'
        tasks[idx]['skipReason'] = 'duplicate — already sent this step'
        write_json(TASKS_FILE, tasks)
        return jsonify({'error': 'Already sent to this person — skipped to prevent duplicate'}), 409
    if task.get('channel') == 'email' and task.get('recipientEmail') and (GMAIL_PASS or RESEND_KEY):
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

_send_lock = threading.Lock()

DAILY_LIMIT = 200

def _already_sent(tasks, lead_id, step):
    """Return True if this lead already has a sent task for this step."""
    return any(
        t.get('fitnessLeadId') == lead_id and
        t.get('sequenceStep') == step and
        t.get('status') == 'sent'
        for t in tasks
    )

def _do_send_all(task_ids):
    """Background thread: send queued emails one at a time with a small delay."""
    import time
    with _send_lock:
        tasks = read_json(TASKS_FILE)
        id_set = set(task_ids)
        email_indices = [(i, task) for i, task in enumerate(tasks)
                         if task.get('id') in id_set and task.get('recipientEmail')]
        for idx, task in email_indices:
            lead_id = task.get('fitnessLeadId')
            step    = task.get('sequenceStep', 0)
            # Safety net: never send if this step was already sent to this person
            if _already_sent(tasks, lead_id, step):
                tasks[idx]['status']     = 'skipped'
                tasks[idx]['skipReason'] = 'duplicate — already sent this step'
                write_json(TASKS_FILE, tasks)
                continue
            try:
                send_email(task['recipientEmail'], task.get('subject', ''), task.get('script', ''))
                tasks[idx]['status'] = 'sent'
                tasks[idx]['sentAt'] = now_iso()
                advance_lead(lead_id, step)
            except Exception as e:
                tasks[idx]['status']     = 'failed'
                tasks[idx]['emailError'] = str(e)
            write_json(TASKS_FILE, tasks)
            time.sleep(1)  # 1 second between emails — avoids Gmail rate limits

@app.route('/api/tasks/approve-all', methods=['POST'])
def approve_all():
    """Queue up to DAILY_LIMIT pending tasks, send in background."""
    tasks = read_json(TASKS_FILE)
    queued_ids = []
    for i, task in enumerate(tasks):
        if len(queued_ids) >= DAILY_LIMIT: break
        if task.get('taskType') != 'fitness_sequence': continue
        if task.get('status') != 'pending': continue
        if task.get('channel') == 'email' and task.get('recipientEmail') and (GMAIL_PASS or RESEND_KEY):
            tasks[i]['status'] = 'queued'
            queued_ids.append(task['id'])
        else:
            tasks[i]['status']     = 'approved'
            tasks[i]['approvedAt'] = now_iso()
    write_json(TASKS_FILE, tasks)
    if queued_ids:
        threading.Thread(target=_do_send_all, args=(queued_ids,), daemon=True).start()
    return jsonify({'queued': len(queued_ids)})

# ── Test email ─────────────────────────────────────────────────────────────────
@app.route('/api/test-email', methods=['POST'])
def test_email():
    if not RESEND_KEY and not GMAIL_PASS:
        return jsonify({'error': 'No email credentials configured'}), 500
    try:
        send_email(GMAIL_USER, 'CRM test - its working', 'Test from your Molly Fitness CRM. Email is sending correctly.\n\nMolly')
        method = 'Resend' if RESEND_KEY else 'Gmail'
        return jsonify({'ok': True, 'to': GMAIL_USER, 'via': method})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ── Clear queue ────────────────────────────────────────────────────────────────
@app.route('/api/tasks/clear', methods=['POST'])
def clear_queue():
    tasks = read_json(TASKS_FILE)
    before = len(tasks)
    tasks = [t for t in tasks if t.get('status') not in ('pending', 'queued')]
    write_json(TASKS_FILE, tasks)
    return jsonify({'removed': before - len(tasks)})

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
    print(f"\nMolly's Fitness CRM -> http://localhost:{PORT}")
    print(f"Gmail: {'Ready' if GMAIL_PASS else 'WARNING: Add GMAIL_APP_PASSWORD to env'}")
    print(f"Leads: {len(read_json(LEADS_FILE))} loaded\n")
    app.run(host='0.0.0.0', port=PORT, debug=False)
