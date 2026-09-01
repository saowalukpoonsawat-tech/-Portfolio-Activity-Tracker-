"""
ระบบบันทึกผลงานส่วนบุคคล (Portfolio & Activity Tracker)
Single-file Flask application (app.py) + Tailwind CSS (CDN)

การใช้งาน:
    pip install flask
    python app.py
    เปิดเบราว์เซอร์ที่ http://127.0.0.1:5000
"""

import os
import sqlite3
from datetime import datetime, date
from functools import wraps

from flask import (
    Flask, request, redirect, url_for, session,
    flash, g, render_template_string, abort
)
from werkzeug.security import generate_password_hash, check_password_hash

# --------------------------------------------------------------------------- #
# Config
# --------------------------------------------------------------------------- #
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "portfolio.db")

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-change-me")

CATEGORIES = ["โปรเจกต์", "งานอบรม/สัมมนา", "รางวัล/เกียรติบัตร",
              "อาสาสมัคร", "การเรียนรู้", "อื่น ๆ"]
STATUSES = ["กำลังทำ", "เสร็จสิ้น", "พัก/รอ"]


# --------------------------------------------------------------------------- #
# Database helpers
# --------------------------------------------------------------------------- #
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            username      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            display_name  TEXT NOT NULL,
            bio           TEXT DEFAULT '',
            created_at    TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS activities (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title        TEXT NOT NULL,
            category     TEXT NOT NULL,
            status       TEXT NOT NULL,
            description  TEXT DEFAULT '',
            skills       TEXT DEFAULT '',
            link         TEXT DEFAULT '',
            activity_date TEXT NOT NULL,
            hours        REAL DEFAULT 0,
            created_at   TEXT NOT NULL,
            updated_at   TEXT NOT NULL
        );
        """
    )
    db.commit()
    db.close()


# --------------------------------------------------------------------------- #
# Auth helpers
# --------------------------------------------------------------------------- #
def current_user():
    uid = session.get("user_id")
    if uid is None:
        return None
    return get_db().execute("SELECT * FROM users WHERE id = ?", (uid,)).fetchone()


@app.context_processor
def inject_globals():
    return dict(current_user=current_user(), CATEGORIES=CATEGORIES,
               STATUSES=STATUSES, now=datetime.now())


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get("user_id") is None:
            flash("กรุณาเข้าสู่ระบบก่อน", "warn")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


# --------------------------------------------------------------------------- #
# Templates (Jinja2 strings)
# --------------------------------------------------------------------------- #
BASE = """
<!doctype html>
<html lang="th">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Portfolio Tracker{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Prompt:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>
    * { font-family: 'Prompt', ui-sans-serif, system-ui, sans-serif; }
  </style>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col">
  <nav class="bg-white border-b border-slate-200 sticky top-0 z-20">
    <div class="max-w-5xl mx-auto px-4 h-16 flex items-center justify-between">
      <a href="{{ url_for('index') }}" class="flex items-center gap-2 font-semibold text-indigo-600">
        <span class="text-2xl">📁</span><span>Portfolio Tracker</span>
      </a>
      <div class="flex items-center gap-1 text-sm">
        {% if current_user %}
          <a href="{{ url_for('dashboard') }}" class="px-3 py-2 rounded-lg hover:bg-slate-100">แดชบอร์ด</a>
          <a href="{{ url_for('activities') }}" class="px-3 py-2 rounded-lg hover:bg-slate-100">ผลงานของฉัน</a>
          <a href="{{ url_for('public_portfolio', username=current_user['username']) }}" class="px-3 py-2 rounded-lg hover:bg-slate-100">พอร์ตสาธารณะ</a>
          <a href="{{ url_for('profile') }}" class="px-3 py-2 rounded-lg hover:bg-slate-100">โปรไฟล์</a>
          <a href="{{ url_for('logout') }}" class="px-3 py-2 rounded-lg text-rose-600 hover:bg-rose-50">ออกจากระบบ</a>
        {% else %}
          <a href="{{ url_for('login') }}" class="px-3 py-2 rounded-lg hover:bg-slate-100">เข้าสู่ระบบ</a>
          <a href="{{ url_for('register') }}" class="px-3 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">สมัครสมาชิก</a>
        {% endif %}
      </div>
    </div>
  </nav>

  <main class="flex-1 max-w-5xl w-full mx-auto px-4 py-8">
    {% with messages = get_flashed_messages(with_categories=true) %}
      {% for cat, msg in messages %}
        <div class="mb-4 rounded-lg px-4 py-3 text-sm border
          {{ 'bg-emerald-50 border-emerald-200 text-emerald-800' if cat == 'ok'
             else 'bg-amber-50 border-amber-200 text-amber-800' if cat == 'warn'
             else 'bg-rose-50 border-rose-200 text-rose-800' }}">
          {{ msg }}
        </div>
      {% endfor %}
    {% endwith %}
    {% block content %}{% endblock %}
  </main>

  <footer class="text-center text-xs text-slate-400 py-6">
    ระบบบันทึกผลงานส่วนบุคคล · สร้างด้วย Flask + Tailwind CSS
  </footer>
</body>
</html>
"""

INDEX = """
{% extends "base" %}
{% block content %}
<div class="text-center py-16">
  <h1 class="text-4xl font-bold text-slate-800 mb-4">บันทึกทุกผลงาน<br>สร้างพอร์ตโฟลิโอของคุณ</h1>
  <p class="text-slate-500 max-w-xl mx-auto mb-8">
    เก็บบันทึกโปรเจกต์ การอบรม รางวัล และกิจกรรมต่าง ๆ ไว้ในที่เดียว
    พร้อมสรุปสถิติและหน้าพอร์ตสาธารณะที่แชร์ได้
  </p>
  {% if current_user %}
    <a href="{{ url_for('dashboard') }}" class="inline-block px-6 py-3 rounded-xl bg-indigo-600 text-white font-medium hover:bg-indigo-700">ไปที่แดชบอร์ด</a>
  {% else %}
    <a href="{{ url_for('register') }}" class="inline-block px-6 py-3 rounded-xl bg-indigo-600 text-white font-medium hover:bg-indigo-700">เริ่มต้นใช้งานฟรี</a>
  {% endif %}
</div>
<div class="grid sm:grid-cols-3 gap-4 mt-8">
  {% for icon, t, d in [
      ('📝','บันทึกง่าย','เพิ่มผลงานพร้อมหมวดหมู่ ทักษะ และลิงก์อ้างอิง'),
      ('📊','เห็นภาพรวม','สรุปจำนวนผลงาน ชั่วโมงสะสม และความคืบหน้า'),
      ('🌐','แชร์พอร์ต','หน้าพอร์ตสาธารณะสำหรับส่งให้ผู้อื่นดู')] %}
    <div class="bg-white border border-slate-200 rounded-xl p-5">
      <div class="text-3xl mb-2">{{ icon }}</div>
      <div class="font-semibold mb-1">{{ t }}</div>
      <div class="text-sm text-slate-500">{{ d }}</div>
    </div>
  {% endfor %}
</div>
{% endblock %}
"""

AUTH = """
{% extends "base" %}
{% block content %}
<div class="max-w-md mx-auto bg-white border border-slate-200 rounded-xl p-6">
  <h1 class="text-xl font-semibold mb-4">{{ 'สมัครสมาชิก' if mode == 'register' else 'เข้าสู่ระบบ' }}</h1>
  <form method="post" class="space-y-4">
    <div>
      <label class="block text-sm mb-1">ชื่อผู้ใช้</label>
      <input name="username" required value="{{ request.form.get('username','') }}"
             class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    </div>
    {% if mode == 'register' %}
    <div>
      <label class="block text-sm mb-1">ชื่อที่แสดง</label>
      <input name="display_name" required value="{{ request.form.get('display_name','') }}"
             class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    </div>
    {% endif %}
    <div>
      <label class="block text-sm mb-1">รหัสผ่าน</label>
      <input type="password" name="password" required
             class="w-full rounded-lg border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500">
    </div>
    <button class="w-full rounded-lg bg-indigo-600 text-white py-2 font-medium hover:bg-indigo-700">
      {{ 'สมัครสมาชิก' if mode == 'register' else 'เข้าสู่ระบบ' }}
    </button>
  </form>
  <p class="text-sm text-slate-500 mt-4">
    {% if mode == 'register' %}
      มีบัญชีแล้ว? <a href="{{ url_for('login') }}" class="text-indigo-600">เข้าสู่ระบบ</a>
    {% else %}
      ยังไม่มีบัญชี? <a href="{{ url_for('register') }}" class="text-indigo-600">สมัครสมาชิก</a>
    {% endif %}
  </p>
</div>
{% endblock %}
"""

DASHBOARD = """
{% extends "base" %}
{% block content %}
<h1 class="text-2xl font-semibold mb-6">สวัสดี, {{ current_user['display_name'] }} 👋</h1>

<div class="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
  {% for label, value, color in [
      ('ผลงานทั้งหมด', stats.total, 'indigo'),
      ('เสร็จสิ้น', stats.done, 'emerald'),
      ('กำลังทำ', stats.doing, 'amber'),
      ('ชั่วโมงสะสม', stats.hours, 'sky')] %}
    <div class="bg-white border border-slate-200 rounded-xl p-4">
      <div class="text-3xl font-bold text-{{ color }}-600">{{ value }}</div>
      <div class="text-sm text-slate-500 mt-1">{{ label }}</div>
    </div>
  {% endfor %}
</div>

<div class="grid md:grid-cols-2 gap-6">
  <div class="bg-white border border-slate-200 rounded-xl p-5">
    <h2 class="font-semibold mb-3">แยกตามหมวดหมู่</h2>
    {% if by_cat %}
      <div class="space-y-2">
        {% for row in by_cat %}
          <div>
            <div class="flex justify-between text-sm mb-1">
              <span>{{ row['category'] }}</span><span class="text-slate-500">{{ row['c'] }}</span>
            </div>
            <div class="h-2 bg-slate-100 rounded-full overflow-hidden">
              <div class="h-full bg-indigo-500 rounded-full"
                   style="width: {{ (row['c'] / stats.total * 100) if stats.total else 0 }}%"></div>
            </div>
          </div>
        {% endfor %}
      </div>
    {% else %}
      <p class="text-sm text-slate-400">ยังไม่มีข้อมูล</p>
    {% endif %}
  </div>

  <div class="bg-white border border-slate-200 rounded-xl p-5">
    <div class="flex items-center justify-between mb-3">
      <h2 class="font-semibold">ผลงานล่าสุด</h2>
      <a href="{{ url_for('new_activity') }}" class="text-sm text-indigo-600">+ เพิ่มผลงาน</a>
    </div>
    {% if recent %}
      <ul class="divide-y divide-slate-100">
        {% for a in recent %}
          <li class="py-2 flex items-center justify-between">
            <a href="{{ url_for('edit_activity', aid=a['id']) }}" class="text-sm hover:text-indigo-600">{{ a['title'] }}</a>
            <span class="text-xs text-slate-400">{{ a['activity_date'] }}</span>
          </li>
        {% endfor %}
      </ul>
    {% else %}
      <p class="text-sm text-slate-400">ยังไม่มีผลงาน — <a href="{{ url_for('new_activity') }}" class="text-indigo-600">เพิ่มเลย</a></p>
    {% endif %}
  </div>
</div>
{% endblock %}
"""

ACTIVITIES = """
{% extends "base" %}
{% block content %}
<div class="flex items-center justify-between mb-6">
  <h1 class="text-2xl font-semibold">ผลงานของฉัน</h1>
  <a href="{{ url_for('new_activity') }}" class="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm hover:bg-indigo-700">+ เพิ่มผลงาน</a>
</div>

<form method="get" class="flex flex-wrap gap-2 mb-4 text-sm">
  <input name="q" value="{{ q }}" placeholder="ค้นหา..."
         class="rounded-lg border border-slate-300 px-3 py-2 flex-1 min-w-[160px]">
  <select name="category" class="rounded-lg border border-slate-300 px-3 py-2">
    <option value="">ทุกหมวดหมู่</option>
    {% for c in CATEGORIES %}<option {{ 'selected' if c == cat }}>{{ c }}</option>{% endfor %}
  </select>
  <select name="status" class="rounded-lg border border-slate-300 px-3 py-2">
    <option value="">ทุกสถานะ</option>
    {% for s in STATUSES %}<option {{ 'selected' if s == status }}>{{ s }}</option>{% endfor %}
  </select>
  <button class="rounded-lg bg-slate-800 text-white px-4 py-2">กรอง</button>
</form>

{% if items %}
  <div class="space-y-3">
    {% for a in items %}
      <div class="bg-white border border-slate-200 rounded-xl p-4">
        <div class="flex items-start justify-between gap-4">
          <div>
            <div class="flex items-center gap-2 flex-wrap">
              <span class="font-semibold">{{ a['title'] }}</span>
              <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">{{ a['category'] }}</span>
              <span class="text-xs px-2 py-0.5 rounded-full
                {{ 'bg-emerald-50 text-emerald-700' if a['status']=='เสร็จสิ้น'
                   else 'bg-amber-50 text-amber-700' if a['status']=='กำลังทำ'
                   else 'bg-slate-100 text-slate-600' }}">{{ a['status'] }}</span>
            </div>
            {% if a['description'] %}<p class="text-sm text-slate-500 mt-1">{{ a['description'] }}</p>{% endif %}
            <div class="text-xs text-slate-400 mt-2 flex gap-3 flex-wrap">
              <span>📅 {{ a['activity_date'] }}</span>
              {% if a['hours'] %}<span>⏱️ {{ a['hours'] }} ชม.</span>{% endif %}
              {% if a['skills'] %}<span>🛠️ {{ a['skills'] }}</span>{% endif %}
              {% if a['link'] %}<a href="{{ a['link'] }}" target="_blank" class="text-indigo-600">🔗 ลิงก์</a>{% endif %}
            </div>
          </div>
          <div class="flex gap-2 shrink-0 text-sm">
            <a href="{{ url_for('edit_activity', aid=a['id']) }}" class="text-slate-500 hover:text-indigo-600">แก้ไข</a>
            <form method="post" action="{{ url_for('delete_activity', aid=a['id']) }}"
                  onsubmit="return confirm('ลบผลงานนี้?')">
              <button class="text-rose-500 hover:text-rose-700">ลบ</button>
            </form>
          </div>
        </div>
      </div>
    {% endfor %}
  </div>
{% else %}
  <div class="bg-white border border-dashed border-slate-300 rounded-xl p-10 text-center text-slate-400">
    ไม่พบผลงาน
  </div>
{% endif %}
{% endblock %}
"""

ACTIVITY_FORM = """
{% extends "base" %}
{% block content %}
<div class="max-w-2xl mx-auto">
  <h1 class="text-2xl font-semibold mb-6">{{ 'แก้ไขผลงาน' if a else 'เพิ่มผลงานใหม่' }}</h1>
  <form method="post" class="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
    <div>
      <label class="block text-sm mb-1">ชื่อผลงาน *</label>
      <input name="title" required value="{{ a['title'] if a else '' }}"
             class="w-full rounded-lg border border-slate-300 px-3 py-2">
    </div>
    <div class="grid sm:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm mb-1">หมวดหมู่ *</label>
        <select name="category" class="w-full rounded-lg border border-slate-300 px-3 py-2">
          {% for c in CATEGORIES %}<option {{ 'selected' if a and a['category']==c }}>{{ c }}</option>{% endfor %}
        </select>
      </div>
      <div>
        <label class="block text-sm mb-1">สถานะ *</label>
        <select name="status" class="w-full rounded-lg border border-slate-300 px-3 py-2">
          {% for s in STATUSES %}<option {{ 'selected' if a and a['status']==s }}>{{ s }}</option>{% endfor %}
        </select>
      </div>
    </div>
    <div class="grid sm:grid-cols-2 gap-4">
      <div>
        <label class="block text-sm mb-1">วันที่ *</label>
        <input type="date" name="activity_date" required
               value="{{ a['activity_date'] if a else today }}"
               class="w-full rounded-lg border border-slate-300 px-3 py-2">
      </div>
      <div>
        <label class="block text-sm mb-1">จำนวนชั่วโมง</label>
        <input type="number" step="0.5" min="0" name="hours"
               value="{{ a['hours'] if a else 0 }}"
               class="w-full rounded-lg border border-slate-300 px-3 py-2">
      </div>
    </div>
    <div>
      <label class="block text-sm mb-1">รายละเอียด</label>
      <textarea name="description" rows="3"
                class="w-full rounded-lg border border-slate-300 px-3 py-2">{{ a['description'] if a else '' }}</textarea>
    </div>
    <div>
      <label class="block text-sm mb-1">ทักษะที่ใช้ (คั่นด้วยเครื่องหมายจุลภาค)</label>
      <input name="skills" value="{{ a['skills'] if a else '' }}"
             class="w-full rounded-lg border border-slate-300 px-3 py-2">
    </div>
    <div>
      <label class="block text-sm mb-1">ลิงก์อ้างอิง</label>
      <input name="link" type="url" value="{{ a['link'] if a else '' }}"
             class="w-full rounded-lg border border-slate-300 px-3 py-2">
    </div>
    <div class="flex gap-2 pt-2">
      <button class="px-5 py-2 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700">บันทึก</button>
      <a href="{{ url_for('activities') }}" class="px-5 py-2 rounded-lg border border-slate-300">ยกเลิก</a>
    </div>
  </form>
</div>
{% endblock %}
"""

PROFILE = """
{% extends "base" %}
{% block content %}
<div class="max-w-2xl mx-auto">
  <h1 class="text-2xl font-semibold mb-6">โปรไฟล์</h1>
  <form method="post" class="bg-white border border-slate-200 rounded-xl p-6 space-y-4">
    <div>
      <label class="block text-sm mb-1">ชื่อที่แสดง</label>
      <input name="display_name" required value="{{ current_user['display_name'] }}"
             class="w-full rounded-lg border border-slate-300 px-3 py-2">
    </div>
    <div>
      <label class="block text-sm mb-1">แนะนำตัว (Bio)</label>
      <textarea name="bio" rows="4"
                class="w-full rounded-lg border border-slate-300 px-3 py-2">{{ current_user['bio'] }}</textarea>
    </div>
    <div class="border-t border-slate-100 pt-4">
      <label class="block text-sm mb-1">เปลี่ยนรหัสผ่าน (เว้นว่างหากไม่เปลี่ยน)</label>
      <input type="password" name="new_password"
             class="w-full rounded-lg border border-slate-300 px-3 py-2">
    </div>
    <button class="px-5 py-2 rounded-lg bg-indigo-600 text-white font-medium hover:bg-indigo-700">บันทึก</button>
  </form>
  <p class="text-sm text-slate-500 mt-4">
    ลิงก์พอร์ตสาธารณะ:
    <a href="{{ url_for('public_portfolio', username=current_user['username']) }}"
       class="text-indigo-600">{{ url_for('public_portfolio', username=current_user['username'], _external=True) }}</a>
  </p>
</div>
{% endblock %}
"""

PUBLIC = """
{% extends "base" %}
{% block content %}
<div class="bg-white border border-slate-200 rounded-xl p-6 mb-6">
  <h1 class="text-2xl font-bold">{{ user['display_name'] }}</h1>
  <p class="text-slate-500">@{{ user['username'] }}</p>
  {% if user['bio'] %}<p class="mt-3 text-slate-600">{{ user['bio'] }}</p>{% endif %}
  <div class="flex gap-4 mt-4 text-sm text-slate-500">
    <span><b class="text-slate-800">{{ items|length }}</b> ผลงาน</span>
    <span><b class="text-slate-800">{{ total_hours }}</b> ชั่วโมงสะสม</span>
  </div>
</div>

{% for a in items %}
  <div class="bg-white border border-slate-200 rounded-xl p-4 mb-3">
    <div class="flex items-center gap-2 flex-wrap">
      <span class="font-semibold">{{ a['title'] }}</span>
      <span class="text-xs px-2 py-0.5 rounded-full bg-indigo-50 text-indigo-700">{{ a['category'] }}</span>
      <span class="text-xs text-slate-400">{{ a['activity_date'] }}</span>
    </div>
    {% if a['description'] %}<p class="text-sm text-slate-500 mt-1">{{ a['description'] }}</p>{% endif %}
    {% if a['skills'] %}<p class="text-xs text-slate-400 mt-2">🛠️ {{ a['skills'] }}</p>{% endif %}
    {% if a['link'] %}<a href="{{ a['link'] }}" target="_blank" class="text-xs text-indigo-600">🔗 ดูผลงาน</a>{% endif %}
  </div>
{% else %}
  <p class="text-center text-slate-400 py-10">ยังไม่มีผลงานที่เผยแพร่</p>
{% endfor %}
{% endblock %}
"""

TEMPLATES = {
    "base": BASE, "index": INDEX, "auth": AUTH, "dashboard": DASHBOARD,
    "activities": ACTIVITIES, "activity_form": ACTIVITY_FORM,
    "profile": PROFILE, "public": PUBLIC,
}


# Enable {% extends "base" %} to resolve from our dict
app.jinja_loader = __import__("jinja2").DictLoader(TEMPLATES)


def render(name, **ctx):
    return render_template_string(TEMPLATES[name], **ctx)


# --------------------------------------------------------------------------- #
# Routes
# --------------------------------------------------------------------------- #
@app.route("/")
def index():
    return render("index")


@app.route("/register", methods=["GET", "POST"])
def register():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        display_name = request.form["display_name"].strip()
        password = request.form["password"]
        db = get_db()
        if not username or not password:
            flash("กรอกข้อมูลให้ครบ", "err")
        elif db.execute("SELECT 1 FROM users WHERE username = ?", (username,)).fetchone():
            flash("ชื่อผู้ใช้นี้ถูกใช้แล้ว", "err")
        else:
            db.execute(
                "INSERT INTO users (username, password_hash, display_name, created_at) "
                "VALUES (?,?,?,?)",
                (username, generate_password_hash(password), display_name or username,
                 datetime.now().isoformat(timespec="seconds")),
            )
            db.commit()
            user = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
            session["user_id"] = user["id"]
            flash("สมัครสมาชิกสำเร็จ", "ok")
            return redirect(url_for("dashboard"))
    return render("auth", mode="register")


@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    if request.method == "POST":
        username = request.form["username"].strip().lower()
        password = request.form["password"]
        user = get_db().execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session["user_id"] = user["id"]
            flash("เข้าสู่ระบบสำเร็จ", "ok")
            nxt = request.args.get("next")
            return redirect(nxt or url_for("dashboard"))
        flash("ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง", "err")
    return render("auth", mode="login")


@app.route("/logout")
def logout():
    session.clear()
    flash("ออกจากระบบแล้ว", "ok")
    return redirect(url_for("index"))


@app.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    uid = session["user_id"]
    rows = db.execute("SELECT * FROM activities WHERE user_id = ?", (uid,)).fetchall()
    total = len(rows)
    done = sum(1 for r in rows if r["status"] == "เสร็จสิ้น")
    doing = sum(1 for r in rows if r["status"] == "กำลังทำ")
    hours = round(sum(r["hours"] or 0 for r in rows), 1)
    stats = {"total": total, "done": done, "doing": doing, "hours": hours}
    by_cat = db.execute(
        "SELECT category, COUNT(*) c FROM activities WHERE user_id = ? "
        "GROUP BY category ORDER BY c DESC", (uid,)
    ).fetchall()
    recent = db.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY date(activity_date) DESC, id DESC LIMIT 5",
        (uid,)
    ).fetchall()
    return render("dashboard", stats=stats, by_cat=by_cat, recent=recent)


@app.route("/activities")
@login_required
def activities():
    q = request.args.get("q", "").strip()
    cat = request.args.get("category", "").strip()
    status = request.args.get("status", "").strip()
    sql = "SELECT * FROM activities WHERE user_id = ?"
    params = [session["user_id"]]
    if q:
        sql += " AND (title LIKE ? OR description LIKE ? OR skills LIKE ?)"
        params += [f"%{q}%"] * 3
    if cat:
        sql += " AND category = ?"
        params.append(cat)
    if status:
        sql += " AND status = ?"
        params.append(status)
    sql += " ORDER BY date(activity_date) DESC, id DESC"
    items = get_db().execute(sql, params).fetchall()
    return render("activities", items=items, q=q, cat=cat, status=status)


def _form_activity():
    return dict(
        title=request.form["title"].strip(),
        category=request.form["category"],
        status=request.form["status"],
        description=request.form.get("description", "").strip(),
        skills=request.form.get("skills", "").strip(),
        link=request.form.get("link", "").strip(),
        activity_date=request.form["activity_date"],
        hours=float(request.form.get("hours") or 0),
    )


@app.route("/activities/new", methods=["GET", "POST"])
@login_required
def new_activity():
    if request.method == "POST":
        d = _form_activity()
        now = datetime.now().isoformat(timespec="seconds")
        get_db().execute(
            "INSERT INTO activities (user_id,title,category,status,description,skills,link,"
            "activity_date,hours,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (session["user_id"], d["title"], d["category"], d["status"], d["description"],
             d["skills"], d["link"], d["activity_date"], d["hours"], now, now),
        )
        get_db().commit()
        flash("เพิ่มผลงานแล้ว", "ok")
        return redirect(url_for("activities"))
    return render("activity_form", a=None, today=date.today().isoformat())


def _owned_activity(aid):
    a = get_db().execute(
        "SELECT * FROM activities WHERE id = ? AND user_id = ?", (aid, session["user_id"])
    ).fetchone()
    if a is None:
        abort(404)
    return a


@app.route("/activities/<int:aid>/edit", methods=["GET", "POST"])
@login_required
def edit_activity(aid):
    a = _owned_activity(aid)
    if request.method == "POST":
        d = _form_activity()
        get_db().execute(
            "UPDATE activities SET title=?,category=?,status=?,description=?,skills=?,link=?,"
            "activity_date=?,hours=?,updated_at=? WHERE id=? AND user_id=?",
            (d["title"], d["category"], d["status"], d["description"], d["skills"], d["link"],
             d["activity_date"], d["hours"], datetime.now().isoformat(timespec="seconds"),
             aid, session["user_id"]),
        )
        get_db().commit()
        flash("บันทึกการแก้ไขแล้ว", "ok")
        return redirect(url_for("activities"))
    return render("activity_form", a=a, today=date.today().isoformat())


@app.route("/activities/<int:aid>/delete", methods=["POST"])
@login_required
def delete_activity(aid):
    _owned_activity(aid)
    get_db().execute("DELETE FROM activities WHERE id = ? AND user_id = ?", (aid, session["user_id"]))
    get_db().commit()
    flash("ลบผลงานแล้ว", "ok")
    return redirect(url_for("activities"))


@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST":
        display_name = request.form["display_name"].strip()
        bio = request.form.get("bio", "").strip()
        new_password = request.form.get("new_password", "")
        if new_password:
            db.execute("UPDATE users SET display_name=?, bio=?, password_hash=? WHERE id=?",
                       (display_name, bio, generate_password_hash(new_password), session["user_id"]))
        else:
            db.execute("UPDATE users SET display_name=?, bio=? WHERE id=?",
                       (display_name, bio, session["user_id"]))
        db.commit()
        flash("บันทึกโปรไฟล์แล้ว", "ok")
        return redirect(url_for("profile"))
    return render("profile")


@app.route("/u/<username>")
def public_portfolio(username):
    db = get_db()
    user = db.execute("SELECT * FROM users WHERE username = ?", (username.lower(),)).fetchone()
    if user is None:
        abort(404)
    items = db.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY date(activity_date) DESC, id DESC",
        (user["id"],)
    ).fetchall()
    total_hours = round(sum(a["hours"] or 0 for a in items), 1)
    return render("public", user=user, items=items, total_hours=total_hours)


@app.errorhandler(404)
def not_found(e):
    return render_template_string(
        BASE.replace("{% block content %}{% endblock %}",
                     '<div class="text-center py-20"><h1 class="text-5xl font-bold text-slate-300">404</h1>'
                     '<p class="mt-2 text-slate-500">ไม่พบหน้าที่คุณต้องการ</p></div>')
    ), 404


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #
if __name__ == "__main__":
    init_db()
    print(" * Portfolio & Activity Tracker")
    print(" * http://127.0.0.1:5001")
    app.run(debug=True)
