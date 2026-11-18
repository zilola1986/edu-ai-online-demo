import sqlite3
import hashlib
import hmac
import secrets
import re
import json
import csv
import io
import base64
from html import escape
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import streamlit as st
from question_bank import SUBJECTS, questions_for, is_grade_specific
from ai_features import available, AIUnavailable, diagnose, generate_questions, tutor
import random

DB = Path(__file__).with_name('edu_ai_v5.db')

def init_db():
    with sqlite3.connect(DB) as con:
        con.execute('''CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL, role TEXT NOT NULL, password_hash TEXT NOT NULL, grade INTEGER, section TEXT, student_id INTEGER)''')
        con.execute('''CREATE TABLE IF NOT EXISTS students (
          id INTEGER PRIMARY KEY AUTOINCREMENT, grade INTEGER NOT NULL,
          section TEXT NOT NULL, nickname TEXT NOT NULL,
          UNIQUE(grade,section,nickname))''')
        con.execute('''CREATE TABLE IF NOT EXISTS attempts (
          id INTEGER PRIMARY KEY AUTOINCREMENT, student_id INTEGER NOT NULL,
          subject TEXT NOT NULL, created_at TEXT NOT NULL, score INTEGER NOT NULL,
          total INTEGER NOT NULL, FOREIGN KEY(student_id) REFERENCES students(id))''')
        con.execute('''CREATE TABLE IF NOT EXISTS teacher_questions (
          id INTEGER PRIMARY KEY AUTOINCREMENT, grade INTEGER NOT NULL, section TEXT NOT NULL,
          subject TEXT NOT NULL, topic TEXT NOT NULL, prompt TEXT NOT NULL,
          options_json TEXT NOT NULL, correct_idx INTEGER NOT NULL,
          explanation TEXT NOT NULL, task TEXT NOT NULL)''')
        con.execute('''CREATE TABLE IF NOT EXISTS topic_results (
          attempt_id INTEGER NOT NULL, topic TEXT NOT NULL, correct INTEGER NOT NULL,
          total INTEGER NOT NULL, FOREIGN KEY(attempt_id) REFERENCES attempts(id))''')

def initialize_demo_accounts():
    """Create demo users from private Streamlit secrets, never from public input."""
    try:
        demo = st.secrets.get('demo_accounts', {})
        credentials = {role: str(demo.get(role, '')).strip() for role in ('admin', 'teacher', 'student')}
    except Exception:
        credentials = {}
    if not credentials or any(len(password) < 10 for password in credentials.values()):
        return False
    with sqlite3.connect(DB) as con:
        con.execute('INSERT OR IGNORE INTO students(grade,section,nickname) VALUES(?,?,?)', (9, 'A', 'Demo-oquvchi-01'))
        student_id = con.execute('SELECT id FROM students WHERE grade=? AND section=? AND nickname=?', (9, 'A', 'Demo-oquvchi-01')).fetchone()[0]
        for username, role, grade, section, sid in (
            ('admin_demo', 'admin', None, None, None),
            ('teacher_demo', 'teacher', 9, 'A', None),
            ('student_demo', 'student', 9, 'A', student_id),
        ):
            exists = con.execute('SELECT 1 FROM users WHERE username=?', (username,)).fetchone()
            if not exists:
                con.execute('INSERT INTO users(username,role,password_hash,grade,section,student_id) VALUES(?,?,?,?,?,?)',
                            (username, role, password_hash(credentials[role]), grade, section, sid))
    return True


def students_in(grade, section):
    with sqlite3.connect(DB) as con:
        return con.execute('SELECT id,nickname FROM students WHERE grade=? AND section=? ORDER BY nickname',(grade,section)).fetchall()

def register(grade, section, nickname):
    with sqlite3.connect(DB) as con:
        con.execute('INSERT OR IGNORE INTO students(grade,section,nickname) VALUES(?,?,?)',(grade,section,nickname))

def save(student_id,subject,score,total,topics):
    with sqlite3.connect(DB) as con:
        cur=con.execute('INSERT INTO attempts(student_id,subject,created_at,score,total) VALUES(?,?,?,?,?)',
                        (student_id,subject,datetime.now().strftime('%Y-%m-%d %H:%M'),score,total))
        con.executemany('INSERT INTO topic_results(attempt_id,topic,correct,total) VALUES(?,?,?,?)',
                        [(cur.lastrowid,t,c,n) for t,(c,n) in topics.items()])


def teacher_questions(grade,section,subject):
    with sqlite3.connect(DB) as con:
        rows=con.execute('SELECT id,topic,prompt,options_json,correct_idx,explanation,task FROM teacher_questions WHERE grade=? AND section=? AND subject=? ORDER BY id', (grade,section,subject)).fetchall()
    return [{'id':r[0], 'topic':r[1], 'q':r[2], 'opts':json.loads(r[3]), 'a':r[4], 'why':r[5], 'task':r[6]} for r in rows]

def add_question(grade,section,subject,topic,prompt,options,answer,explanation,task):
    with sqlite3.connect(DB) as con:
        con.execute('INSERT INTO teacher_questions(grade,section,subject,topic,prompt,options_json,correct_idx,explanation,task) VALUES(?,?,?,?,?,?,?,?,?)',
                    (grade,section,subject,topic,prompt,json.dumps(options,ensure_ascii=False),answer,explanation,task))

BULK_HEADERS = ["mavzu","savol","A","B","C","D","togri_javob","izoh","tavsiya"]

def parse_bulk_csv(uploaded):
    """UTF-8 CSV; accepts Excel-saved UTF-8 BOM and semicolon delimiters."""
    raw = uploaded.getvalue()
    if len(raw)>2_000_000:
        raise ValueError("Fayl hajmi 2 MB dan oshmasin.")
    try:
        content=raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValueError("CSV faylni UTF-8 formatida saqlang.")
    try:
        dialect=csv.Sniffer().sniff(content[:4096],delimiters=",;\\t")
    except csv.Error:
        dialect=csv.excel
    reader=csv.DictReader(io.StringIO(content),dialect=dialect)
    if reader.fieldnames is None or [h.strip() for h in reader.fieldnames]!=BULK_HEADERS:
        raise ValueError("Ustunlar namunadagi tartibda bo‘lishi kerak: "+", ".join(BULK_HEADERS))
    rows=[]
    errors=[]
    for line_no,row in enumerate(reader,start=2):
        if None in row:
            errors.append(f"{line_no}-qator: ustunlar soni noto‘g‘ri."); continue
        values={k:(v or "").strip() for k,v in row.items()}
        if not any(values.values()): continue
        if not all(values[k] for k in BULK_HEADERS[:7]):
            errors.append(f"{line_no}-qator: mavzu, savol, 4 variant va to‘g‘ri javob majburiy."); continue
        if values["togri_javob"].upper() not in ("A","B","C","D"):
            errors.append(f"{line_no}-qator: to‘g‘ri javob A, B, C yoki D bo‘lsin."); continue
        options=[values[x] for x in "ABCD"]
        if len({x.casefold() for x in options})!=4:
            errors.append(f"{line_no}-qator: javob variantlari har xil bo‘lishi kerak."); continue
        if len(values["savol"])>2000 or any(len(x)>500 for x in options):
            errors.append(f"{line_no}-qator: savol yoki javob juda uzun."); continue
        rows.append((values["mavzu"],values["savol"],options,"ABCD".index(values["togri_javob"].upper()),
                     values["izoh"] or "Izoh kiritilmagan.",values["tavsiya"] or "Mavzuni takrorlang."))
    if not rows and not errors: errors.append("Faylda savollar yo‘q.")
    
    return rows,errors

def insert_bulk_questions(grade,section,subject,rows):
    with sqlite3.connect(DB) as con:
        con.executemany(
            "INSERT INTO teacher_questions(grade,section,subject,topic,prompt,options_json,correct_idx,explanation,task) VALUES(?,?,?,?,?,?,?,?,?)",
            [(grade,section,subject,topic,prompt,json.dumps(options,ensure_ascii=False),answer,explanation,task)
             for topic,prompt,options,answer,explanation,task in rows]
        )

def csv_template():
    stream=io.StringIO()
    writer=csv.writer(stream)
    writer.writerow(BULK_HEADERS)
    writer.writerow(["Kasrlar","1/2 + 1/2 = ?","1","2","1/2","0","A",
                     "Yarim va yarim bir butun bo‘ladi.","Kasrlarni qo‘shishni takrorlang."])
    return stream.getvalue().encode("utf-8-sig")

def delete_question(question_id):
    with sqlite3.connect(DB) as con:
        con.execute('DELETE FROM teacher_questions WHERE id=?',(question_id,))

def level(p):
    return 'Yaxshi o‘zlashtirilgan' if p>=80 else 'Mustahkamlash kerak' if p>=50 else 'Qo‘shimcha yordam kerak'


def password_hash(password):
    salt=secrets.token_bytes(16)
    digest=hashlib.pbkdf2_hmac('sha256',password.encode(),salt,310000)
    return salt.hex()+':'+digest.hex()

def password_ok(password,stored):
    try:
        salt,digest=stored.split(':')
        got=hashlib.pbkdf2_hmac('sha256',password.encode(),bytes.fromhex(salt),310000)
        return hmac.compare_digest(got,bytes.fromhex(digest))
    except (ValueError,TypeError): return False

def create_account(username,password,role,grade=None,section=None,student_id=None):
    username=username.strip().lower()
    if not re.fullmatch('[a-z0-9_.-]{3,32}',username): raise ValueError('Login 3–32 ta lotin harfi/raqam yoki ._- belgilaridan iborat bo‘lsin.')
    if len(password)<10: raise ValueError('Parol kamida 10 belgidan iborat bo‘lsin.')
    with sqlite3.connect(DB) as con:
        con.execute('INSERT INTO users(username,role,password_hash,grade,section,student_id) VALUES(?,?,?,?,?,?)',(username,role,password_hash(password),grade,section,student_id))

def current_user():
    uid=st.session_state.get('user_id')
    if not uid: return None
    with sqlite3.connect(DB) as con:
        row=con.execute('SELECT id,username,role,grade,section,student_id FROM users WHERE id=?',(uid,)).fetchone()
    return row

def accounts_page(user):
    st.subheader('🔐 Login va parollarni boshqarish')
    role=user[2]
    # Sinf va hisob turi formadan tashqarida: tanlov o'zgarganda Streamlit
    # qayta ishga tushadi va o'quvchilar ro'yxati darhol yangilanadi.
    typ=st.selectbox('Hisob turi',['teacher','student'] if role=='admin' else ['student'],
                     format_func=lambda r:{'teacher':'O‘qituvchi','student':'O‘quvchi'}[r],
                     key='account_type')
    grade,section=None,None
    if typ=='student':
        if role=='admin':
            grade=st.selectbox('Sinf',list(range(1,12)),index=8,key='account_grade')
            section=st.selectbox('Sinf harfi',['A','B','C','D','E'],key='account_section')
        else:
            grade,section=user[3],user[4]
            st.info(f'Hisob ochiladigan sinf: {grade}-{section}')
    sid=None
    if typ=='student':
        students=students_in(grade,section)
        if not students:
            st.warning(f'{grade}-{section} sinfida o‘quvchi topilmadi. Avval “Sinf va o‘quvchilar” bo‘limida qo‘shing.')
        sid=st.selectbox('O‘quvchi', [None]+[x[0] for x in students],
                         format_func=lambda i:'Tanlanmagan' if i is None else next((name for k,name in students if k==i),'Noma’lum'),
                         key=f'account_student_{grade}_{section}')
    with st.form('create_user'):
        login=st.text_input('Yangi login')
        pw=st.text_input('Yangi parol (kamida 10 belgi)',type='password')
        if st.form_submit_button('Hisob yaratish'):
            if typ=='student' and sid is None:
                st.error('Avval o‘quvchini tanlang.')
            else:
                try:
                    create_account(login,pw,typ,grade,section,sid if typ=='student' else None)
                    st.success('Hisob yaratildi!')
                except (ValueError,sqlite3.IntegrityError) as e:
                    st.error(str(e))
    st.subheader('Parolni yangilash')
    with sqlite3.connect(DB) as con:
        if role=='admin': rows=con.execute('SELECT id,username,role FROM users ORDER BY username').fetchall()
        else: rows=con.execute("SELECT id,username,role FROM users WHERE role='student' AND grade=? AND section=? ORDER BY username", (user[3],user[4])).fetchall()
    with st.form('reset_password'):
        selected=st.selectbox('Hisob',rows,format_func=lambda x:x[1]+' ('+x[2]+')') if rows else None
        new_pw=st.text_input('Yangi parol',type='password')
        if st.form_submit_button('Parolni almashtirish') and selected:
            if len(new_pw)<10: st.error('Kamida 10 belgi kiriting.')
            else:
                with sqlite3.connect(DB) as con: con.execute('UPDATE users SET password_hash=? WHERE id=?',(password_hash(new_pw),selected[0]))
                st.success('Parol yangilandi.')
    st.caption('Parollar ko‘rsatilmaydi; administrator yoki sinf o‘qituvchisi yangisini belgilashi mumkin.')

st.set_page_config(page_title='EDU AI — Chap menyu',page_icon='🎓',layout='wide',initial_sidebar_state='expanded')
# Foydalanuvchi yuborgan rasmni asosiy sahifa foniga joylash.
# Sidebar o‘zining to‘q ko‘k rangini saqlaydi.
BG_FILE = Path(__file__).with_name('edu_ai_background.jpg')
BG_DATA = base64.b64encode(BG_FILE.read_bytes()).decode('ascii')
st.markdown("""<style>
[data-testid="stAppViewContainer"] {  background-image: linear-gradient(rgba(255,255,255,0.75),rgba(255,255,255,0.75)), url('data:image/jpeg;base64,__EDU_AI_BG_DATA__');
  background-size: cover;
  background-position: center center;
  background-attachment: fixed;
  background-repeat: no-repeat;
}
[data-testid="stAppViewContainer"] [data-testid="stHeader"] {background:rgba(255,255,255,0.65);}
[data-testid="stAppViewContainer"] [data-testid="stForm"] {background:rgba(255,255,255,0.90);border-radius:14px;padding:14px;}
[data-testid="stAppViewContainer"] [data-testid="stVerticalBlockBorderWrapper"] {border-radius:12px;}
</style>""".replace("__EDU_AI_BG_DATA__", BG_DATA),unsafe_allow_html=True)
st.markdown("""<style>
/* Chap navigatsiya paneli; asosiy sahifalar o‘zgarmaydi. */
[data-testid="stSidebar"] {background:linear-gradient(180deg,#101f3a 0%,#172b4d 100%);min-width:270px;max-width:310px;}
[data-testid="stSidebar"] * {color:#f1f5f9;}
[data-testid="stSidebar"] [data-testid="stRadio"] > div {gap:0.4rem;}
[data-testid="stSidebar"] [data-testid="stRadio"] label {padding:0.68rem 0.75rem;border-radius:0.75rem;background:rgba(255,255,255,.055);border:1px solid rgba(255,255,255,.08);transition:background .15s ease;cursor:pointer;}
[data-testid="stSidebar"] [data-testid="stRadio"] label:hover {background:rgba(255,255,255,.15);}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) {background:#2563eb;border-color:#60a5fa;}
[data-testid="stSidebar"] [data-testid="stRadio"] label [data-testid="stMarkdownContainer"] p {font-weight:600;font-size:0.94rem;}
[data-testid="stSidebar"] button {border-radius:0.7rem;border:1px solid #64748b;}
[data-testid="stSidebar"] [data-testid="stAlert"] {background:rgba(16,185,129,.16);border:1px solid rgba(52,211,153,.3);}
[data-testid="stSidebar"] [data-testid="stAlert"] * {color:#d1fae5;}
[data-testid="stSidebarCollapseButton"] * {color:inherit;}
.block-container {padding-top:2rem;max-width:1250px;}
@media(max-width:768px){[data-testid="stSidebar"]{min-width:240px;}}
</style>""",unsafe_allow_html=True)
init_db()
st.title('🎓 EDU AI 6.0 — Sun’iy intellektli ta’lim platformasi')
if not initialize_demo_accounts():
    st.error('Demo hisoblar sozlanmagan. Streamlit Secrets bo‘limida [demo_accounts] uchun admin, teacher va student parollarini kiriting (kamida 10 belgi).')
    st.stop()
user=current_user()
if user is None:
    with st.form('login_form'):
        uname=st.text_input('Login')
        pwd=st.text_input('Parol',type='password')
        if st.form_submit_button('Kirish',type='primary'):
            with sqlite3.connect(DB) as con:
                found=con.execute('SELECT id,password_hash FROM users WHERE username=?',(uname.strip().lower(),)).fetchone()
            if found and password_ok(pwd,found[1]): st.session_state['user_id']=found[0]; st.rerun()
            else: st.error('Login yoki parol noto‘g‘ri.')
    st.stop()
role=user[2]
st.sidebar.markdown('## 🎓 EDU AI')
st.sidebar.caption('BOSHQARUV PANELI')

# Foydalanuvchi kartasi va chiqish tugmasining zamonaviy ko‘rinishi.
st.sidebar.markdown("""<style>
[data-testid="stSidebar"] .edu-profile-card {
  background: linear-gradient(125deg, #213e6a, #172a4b);
  border: 1px solid rgba(147,197,253,.38);
  border-radius: 17px;
  padding: 16px 13px;
  margin: 13px 0 10px;
  box-shadow: 0 8px 22px rgba(3,10,25,.22);
}
[data-testid="stSidebar"] .edu-profile-top {display:flex;align-items:center;gap:11px;}
[data-testid="stSidebar"] .edu-profile-avatar {
  width:44px;height:44px;flex-shrink:0;display:flex;align-items:center;
  justify-content:center;border-radius:14px;
  background:linear-gradient(135deg,#38bdf8,#6366f1);font-size:24px;
}
[data-testid="stSidebar"] .edu-profile-name {
  color:#fff;font-size:15px;font-weight:750;overflow-wrap:anywhere;
}
[data-testid="stSidebar"] .edu-profile-role {color:#bfdbfe;font-size:12px;margin-top:3px;}
[data-testid="stSidebar"] .edu-profile-status {
  display:inline-flex;align-items:center;gap:7px;margin-top:13px;
  font-size:11px;color:#d1fae5;
}
[data-testid="stSidebar"] .edu-profile-dot {
  display:inline-block;width:8px;height:8px;border-radius:50%;background:#34d399;
  box-shadow:0 0 0 3px rgba(52,211,153,.15);
}
[data-testid="stSidebar"] .st-key-edu_logout_btn button {
  background:linear-gradient(90deg,#ef4444,#dc2626)!important;
  border:1px solid #f87171!important;border-radius:12px!important;
  color:#fff!important;font-weight:700!important;min-height:43px;
  box-shadow:0 4px 12px rgba(239,68,68,.18);
}
[data-testid="stSidebar"] .st-key-edu_logout_btn button:hover {
  background:linear-gradient(90deg,#dc2626,#b91c1c)!important;
  border-color:#fca5a5!important;
}
</style>""", unsafe_allow_html=True)
role_names = {'admin':'Administrator','teacher':'O‘qituvchi','student':'O‘quvchi'}
role_icons = {'admin':'🛡️','teacher':'👩‍🏫','student':'🎓'}
profile_name = escape(str(user[1]))
profile_role = role_names.get(role, 'Foydalanuvchi')
profile_icon = role_icons.get(role, '👤')
st.sidebar.markdown(f"""
<div class="edu-profile-card">
  <div class="edu-profile-top">
    <div class="edu-profile-avatar">{profile_icon}</div>
    <div>
      <div class="edu-profile-name">{profile_name}</div>
      <div class="edu-profile-role">{profile_role} hisobi</div>
    </div>
  </div>
  <div class="edu-profile-status"><span class="edu-profile-dot"></span> Tizimga kirilgan</div>
</div>
""", unsafe_allow_html=True)
if st.sidebar.button('🚪 Hisobdan chiqish', key='edu_logout_btn', use_container_width=True):
    st.session_state.pop('user_id',None)
    st.rerun()
if role=='student': pages=['O‘quvchi testi','AI diagnostika','Adaptiv mashqlar','AI repetitor']
elif role=='teacher': pages=['Sinf va o‘quvchilar','O‘qituvchi paneli','Savollarni boshqarish','Hisoblar']
else: pages=['Sinf va o‘quvchilar','Hisoblar','Savollarni boshqarish']
st.sidebar.markdown('---')
page=st.sidebar.radio('📌 Bo‘limlar',pages)
st.sidebar.caption('🟢 AI ulangan' if available() else '🟠 AI API kaliti ulanmagan')

if page == 'AI diagnostika':
    st.subheader('🧠 AI bilim diagnostikasi')
    st.caption('Test natijalari mavzular bo‘yicha tahlil qilinadi. AI faqat fan, sinf va yig‘ma natijalarni oladi; taxallus va parol yuborilmaydi.')
    with sqlite3.connect(DB) as con:
        if role=='student':
            rows=con.execute('SELECT a.id,a.subject,a.created_at,a.score,a.total,s.grade FROM attempts a JOIN students s ON s.id=a.student_id WHERE a.student_id=? ORDER BY a.id DESC LIMIT 50',(user[5],)).fetchall()
        elif role=='teacher':
            rows=con.execute('SELECT a.id,a.subject,a.created_at,a.score,a.total,s.grade FROM attempts a JOIN students s ON s.id=a.student_id ORDER BY a.id DESC LIMIT 100').fetchall()
        else:
            rows=con.execute('SELECT a.id,a.subject,a.created_at,a.score,a.total,s.grade FROM attempts a JOIN students s ON s.id=a.student_id ORDER BY a.id DESC LIMIT 100').fetchall()
    if not rows:
        st.warning('Avval o‘quvchi testini topshiring.')
    else:
        selected=st.selectbox('Test natijasi',rows,format_func=lambda r:f'#{r[0]} · {r[1]} · {r[2]} · {r[3]}/{r[4]}')
        with sqlite3.connect(DB) as con:
            ts=con.execute('SELECT topic,correct,total FROM topic_results WHERE attempt_id=?',(selected[0],)).fetchall()
        topics={t:(c,n) for t,c,n in ts}
        for t,(c,n) in topics.items():
            st.write(f'{t}: {c}/{n} — {level(100*c/n)}')
        if st.button('✨ AI tahlil va individual reja yaratish',type='primary'):
            try:
                with st.spinner('AI tahlil qilmoqda...'):
                    st.session_state['diagnosis']=(selected[0],diagnose(selected[1],selected[5],topics))
            except AIUnavailable as e: st.error(str(e))
        if st.session_state.get('diagnosis',(None,None))[0]==selected[0]:
            st.markdown(st.session_state['diagnosis'][1])

elif page == 'AI test generatori':
    st.subheader('✨ AI test generatori')
    if role=='student':
        st.info('O‘zingiz uchun AI yordamida mashq savollari yarating. Savollar o‘qituvchining bazasiga saqlanmaydi.')
    else:
        st.warning('AI yaratgan savollarni o‘qituvchi tekshirib tasdiqlashi shart. Savollar avtomatik ravishda bazaga qo‘shilmaydi.')
    with st.form('gen_form'):
        c1,c2,c3=st.columns(3)
        grade=c1.selectbox('Sinf',list(range(1,12)),index=(user[3]-1 if role=='student' and user[3] else 8),disabled=(role=='student'))
        section=c2.selectbox('Sinf harfi',list('ABCDE'),index=(list('ABCDE').index(user[4]) if role=='student' and user[4] in 'ABCDE' else 0),disabled=(role=='student'))
        subject=c3.selectbox('Fan',SUBJECTS)
        topic=st.text_input('Mavzu',value='Python shart operatorlari')
        count=st.slider('Savollar soni',1,10,5)
        difficulty=st.selectbox('Qiyinlik',['Oson','O‘rta','Murakkab'])
        go=st.form_submit_button('AI yordamida savollar yaratish',type='primary')
    if go:
        if len(topic.strip())<3: st.error('Mavzuni to‘liq yozing.')
        else:
            try:
                with st.spinner('Savollar yaratilmoqda...'):
                    generated=generate_questions(subject,grade,topic.strip(),count,difficulty)
                st.session_state['generated']={'grade':grade,'section':section,'subject':subject,'questions':generated}
            except AIUnavailable as e: st.error(str(e))
    batch=st.session_state.get('generated')
    if batch:
        st.info(f"Tayyorlangan savollar: {batch['grade']}-{batch['section']} · {batch['subject']}.")
        if role=='student':
            st.caption('Bu savollar faqat mustaqil mashq uchun. AI javoblarini tekshirib ko‘ring.')
            for i,q in enumerate(batch['questions']):
                with st.expander(f"{i+1}. {q['q'][:100]}",expanded=i==0):
                    st.write(q['q'])
                    for j,opt in enumerate(q['opts']):
                        st.write(f"{'ABCD'[j]}) {opt}")
                    with st.expander('To‘g‘ri javob va izoh'):
                        st.success(f"To‘g‘ri javob: {'ABCD'[q['a']]}) {q['opts'][q['a']]}")
                        st.write(q['why'])
                        st.caption('Mashq: '+q['task'])
        else:
            with st.form('approve_generated'):
                approvals=[]
                for i,q in enumerate(batch['questions']):
                    with st.expander(f"{i+1}. {q['q'][:100]}",expanded=i==0):
                        st.write(q['q'])
                        for j,opt in enumerate(q['opts']): st.write(f"{'ABCD'[j]}) {opt}"+(' ✅' if j==q['a'] else ''))
                        st.caption('Izoh: '+q['why'])
                        st.caption('Mashq: '+q['task'])
                        approvals.append(st.checkbox('Ushbu savolni tasdiqlayman',key=f'approve_{i}'))
                save_gen=st.form_submit_button('Tasdiqlangan savollarni bazaga saqlash')
            if save_gen:
                chosen=[q for q,ok in zip(batch['questions'],approvals) if ok]
                if not chosen: st.warning('Kamida bitta savolni tasdiqlang.')
                else:
                    insert_bulk_questions(batch['grade'],batch['section'],batch['subject'],[(q['topic'],q['q'],q['opts'],q['a'],q['why'],q['task']) for q in chosen])
                    st.session_state.pop('generated',None)
                    st.success(f'{len(chosen)} ta savol saqlandi!')
                    st.rerun()

elif page == 'AI repetitor':
    st.subheader('💬 AI virtual repetitor')
    grade=user[3] if role=='student' else st.selectbox('Sinf',list(range(1,12)),index=8,key='tutor_grade')
    subject=st.selectbox('Fan',SUBJECTS,key='tutor_subject')
    with st.form('tutor_form'):
        question=st.text_area('Savolingizni yozing',placeholder='Masalan: Python for siklini misol bilan tushuntir',max_chars=1500)
        submit=st.form_submit_button('AI dan tushuntirish olish',type='primary')
    if submit:
        if len(question.strip())<5: st.warning('Savolingizni to‘liq yozing.')
        else:
            try:
                with st.spinner('AI javob tayyorlamoqda...'):
                    st.session_state['tutor_answer']=tutor(subject,grade,question.strip())
            except AIUnavailable as e: st.error(str(e))
    if st.session_state.get('tutor_answer'): st.markdown(st.session_state['tutor_answer'])

elif page == 'Adaptiv mashqlar':
    st.subheader('🎯 Adaptiv mashqlar')
    st.caption('Natijalarga qarab mavzu va qiyinlik tanlanadi; AI ulangan bo‘lsa, aynan shu darajaga mos yangi savollar yaratadi. Qiyinlikni tanlash algoritmik, savollarni yaratish esa AI yordamida bajariladi.')
    with sqlite3.connect(DB) as con:
        if role=='student':
            rows=con.execute('SELECT a.subject,tr.topic,SUM(tr.correct),SUM(tr.total),s.grade FROM attempts a JOIN topic_results tr ON tr.attempt_id=a.id JOIN students s ON s.id=a.student_id WHERE a.student_id=? GROUP BY a.subject,tr.topic,s.grade',(user[5],)).fetchall()
        elif role=='teacher':
            rows=con.execute('SELECT a.subject,tr.topic,SUM(tr.correct),SUM(tr.total),s.grade FROM attempts a JOIN topic_results tr ON tr.attempt_id=a.id JOIN students s ON s.id=a.student_id GROUP BY a.subject,tr.topic,s.grade').fetchall()
        else:
            rows=con.execute('SELECT a.subject,tr.topic,SUM(tr.correct),SUM(tr.total),s.grade FROM attempts a JOIN topic_results tr ON tr.attempt_id=a.id JOIN students s ON s.id=a.student_id GROUP BY a.subject,tr.topic,s.grade').fetchall()
    if not rows:
        st.warning('Avval test topshirib natija to‘plang.')
    else:
        chosen=st.selectbox('Mavzu va fan',rows,format_func=lambda r:f'{r[0]} · {r[1]} · {r[2]}/{r[3]}')
        subject,topic,correct,total,grade=chosen
        pct=100*correct/total
        difficulty='Oson' if pct<50 else 'O‘rta' if pct<80 else 'Murakkab'
        st.metric('O‘zlashtirish',f'{pct:.0f}%')
        st.info(f'Tavsiya etilgan qiyinlik: **{difficulty}**. AI 3 ta yangi mashq yaratishi mumkin.')
        if st.button('✨ Menga mos 3 ta AI mashq yaratish',type='primary'):
            try:
                with st.spinner('Mos mashqlar yaratilmoqda...'):
                    st.session_state['adaptive']=(subject,topic,generate_questions(subject,grade,topic,3,difficulty))
            except AIUnavailable as e: st.error(str(e))
        cached=st.session_state.get('adaptive')
        if cached and cached[:2]==(subject,topic):
            with st.form('adaptive_quiz'):
                answers=[]
                for i,q in enumerate(cached[2]):
                    st.write(f"**{i+1}. {q['q']}**")
                    answers.append(st.radio('Javob',q['opts'],index=None,key=f'adapt_{i}'))
                done=st.form_submit_button('Mashqlarni tekshirish')
            if done:
                if any(a is None for a in answers): st.warning('Barcha savollarga javob bering.')
                else:
                    score=sum(a==q['opts'][q['a']] for q,a in zip(cached[2],answers))
                    st.success(f'Natija: {score}/{len(answers)}')
                    for q,a in zip(cached[2],answers):
                        if a!=q['opts'][q['a']]: st.write(f"**{q['q']}** — {q['why']}")
                    st.caption('Bu qo‘shimcha mashq natijasi asosiy testlar tarixiga saqlanmaydi.')

elif page == 'Hisoblar':
    accounts_page(user)
elif page == 'Mening natijalarim':
    st.subheader('📈 Mening natijalarim')
    with sqlite3.connect(DB) as con:
        rows=con.execute('SELECT subject,created_at,score,total FROM attempts WHERE student_id=? ORDER BY id DESC',(user[5],)).fetchall()
    if not rows: st.info('Hali natija yo‘q.')
    for subject,date,score,total in rows: st.write(f'{date} · {subject}: {score}/{total} ({round(score/total*100)}%)')
elif page == 'Sinf va o‘quvchilar':
    st.subheader('Sinfga o‘quvchi qo‘shish')
    c1,c2=st.columns(2)
    grade=c1.selectbox('Sinf',list(range(1,12)),index=(user[3]-1 if role=='teacher' and user[3] else 0),format_func=lambda n:f'{n}-sinf',disabled=(role=='teacher'))
    section=c2.selectbox('Sinf harfi',['A','B','C','D','E'],index=(['A','B','C','D','E'].index(user[4]) if role=='teacher' and user[4] in 'ABCDE' else 0),disabled=(role=='teacher'))
    with st.form('add_student'):
        nickname=st.text_input('O‘quvchi taxallusi (masalan, Oquvchi-01)',max_chars=60)
        if st.form_submit_button('O‘quvchini qo‘shish'):
            if not nickname.strip(): st.warning('Taxallus kiriting.')
            else:
                register(grade,section,nickname.strip())
                st.success('O‘quvchi ro‘yxatga qo‘shildi (yoki avvaldan mavjud).')
    rows=students_in(grade,section)
    st.write(f'**{grade}-{section} sinf o‘quvchilari: {len(rows)} nafar**')
    for sid,name in rows: st.write(f'#{sid} — {name}')
    st.caption('Namoyishda haqiqiy o‘quvchi F.I.Sh. o‘rniga taxalluslardan foydalaning.')

elif page == 'O‘quvchi testi':
    c1,c2,c3=st.columns(3)
    grade=c1.selectbox('Sinf',list(range(1,12)),index=(user[3]-1 if role=='student' else 8),format_func=lambda n:f'{n}-sinf',disabled=(role=='student'))
    section=c2.selectbox('Sinf harfi',['A','B','C','D','E'],index=(['A','B','C','D','E'].index(user[4]) if role=='student' else 0),disabled=(role=='student'))
    subject=c3.selectbox('Fan',SUBJECTS)
    students=students_in(grade,section)
    if not students:
        st.warning(f'{grade}-{section} sinfida hali o‘quvchi yo‘q. Avval “Sinf va o‘quvchilar” bo‘limida taxallus qo‘shing.')
    else:
        allowed=[row[0] for row in students] if role!='student' else [user[5]]
        if role=='student' and user[5] not in [row[0] for row in students]:
            st.error('O‘quvchi hisobi sinfga mos emas. Administratorga murojaat qiling.'); st.stop()
        sid=st.selectbox('O‘quvchini tanlang',allowed,format_func=lambda i:next(name for k,name in students if k==i),disabled=(role=='student'))
        custom=teacher_questions(grade,section,subject)
        questions=custom if custom else questions_for(subject,grade)
        if questions:
            count=st.number_input('Testda nechta savol chiqsin?',min_value=1,max_value=len(questions),value=len(questions),step=1)
            questions=questions[:int(count)]
        if not questions:
            st.warning(f'{grade}-sinf uchun {subject} fanidan demo savollar mavjud emas.')
        else:
            st.subheader(f'{grade}-{section} · {subject} · {len(questions)} ta savol')
            if custom:
                st.caption('Bu sinf uchun o‘qituvchi kiritgan savollar ishlatilmoqda.')
            elif not is_grade_specific(subject):
                st.caption('Bu fan savollari hozircha sinflar uchun umumiy namunaviy bankdan olingan.')
            else:
                st.caption('Bu fan savollari sinf darajasi uchun alohida tanlangan namunaviy savollardir; rasmiy o‘quv dasturi to‘liq qamrab olinmagan.')
            with st.form(f'quiz_{grade}_{section}_{sid}_{subject}_{len(questions)}'):
                answers=[]
                for i,q in enumerate(questions):
                    st.markdown(f'**{i+1}. [{q["topic"]}] {q["q"]}**')
                    # Different answer order per student, deterministic across reruns
                    shift=(sid+i)%len(q['opts'])
                    opts=q['opts'][shift:]+q['opts'][:shift]
                    answers.append(st.radio('Javob',opts,index=None,key=f'a_{grade}_{section}_{sid}_{subject}_{len(questions)}_{i}',label_visibility='collapsed'))
                    st.divider()
                submitted=st.form_submit_button('Natijani tahlil qilish',type='primary')
            if submitted:
                if any(a is None for a in answers): st.warning('Barcha savollarga javob bering.')
                else:
                    totals=defaultdict(int); correct=defaultdict(int); wrong=[]; score=0
                    for q,a in zip(questions,answers):
                        totals[q['topic']]+=1
                        if a==q['opts'][q['a']]: score+=1; correct[q['topic']]+=1
                        else: wrong.append(q)
                    topics={t:(correct[t],n) for t,n in totals.items()}
                    save(sid,subject,score,len(questions),topics)
                    st.success('Natija aynan tanlangan o‘quvchiga saqlandi!')
                    pct=round(100*score/len(questions))
                    x,y,z=st.columns(3)
                    x.metric('To‘g‘ri javob',f'{score}/{len(questions)}')
                    y.metric('Natija',f'{pct}%')
                    z.metric('Tahlil',level(pct))
                    st.subheader('Mavzular bo‘yicha tahlil')
                    for topic,(c,n) in topics.items():
                        p=round(100*c/n); st.write(f'**{topic}: {p}% — {level(p)}**'); st.progress(p/100)
                    st.subheader('Individual mashqlar')
                    for topic,(c,n) in sorted(topics.items(),key=lambda item:item[1][0]/item[1][1]):
                        st.markdown(f'**{topic}**')
                        if c/n < .8:
                            for task in dict.fromkeys(q['task'] for q in questions if q['topic']==topic): st.write('• '+task)
                        else: st.write('• Murakkabroq mashqlarga o‘ting.')
                    if wrong:
                        with st.expander('Xatolar va tushuntirishlar'):
                            for q in wrong:
                                st.write('**'+q['q']+'**')
                                st.write('To‘g‘ri javob: '+q['opts'][q['a']])
                                st.caption(q['why'])

elif page == 'Savollarni boshqarish':
    st.subheader('📝 O‘qituvchi savollar bazasi')
    st.caption('Bu bo‘lim faqat o‘qituvchi va administratorga ochiq.')
    c1,c2,c3=st.columns(3)
    grade=c1.selectbox('Sinf',list(range(1,12)),index=8,format_func=lambda n:f'{n}-sinf',key='teacher_grade',disabled=False)
    section=c2.selectbox('Sinf harfi',['A','B','C','D','E'],key='teacher_section',index=0,disabled=False)
    subject=c3.selectbox('Fan',SUBJECTS,key='teacher_subject')
    st.caption(f'{grade}-{section} / {subject}: savollar faqat shu sinf va fan uchun saqlanadi. Agar savollar kiritilgan bo‘lsa, shu sinfda demo savollar o‘rniga ular ishlatiladi.')
    with st.form('new_teacher_question',clear_on_submit=True):
        topic=st.text_input('Mavzu',placeholder='Masalan: Kasrlar')
        prompt=st.text_area('Savol matni',placeholder='Masalan: 1/2 + 1/2 = ?')
        opts=[st.text_input(f'{letter} javob varianti',key=f'opt_{letter}') for letter in 'ABCD']
        answer=st.selectbox('To‘g‘ri javob',['A','B','C','D'])
        explanation=st.text_area('Javob izohi',placeholder='Nega shu javob to‘g‘ri?')
        task=st.text_input('Individual tavsiya / mashq',placeholder='Mavzuni takrorlang va 5 ta misol ishlang')
        submitted=st.form_submit_button('Savolni saqlash',type='primary')
        if submitted:
            if not topic.strip() or not prompt.strip() or any(not x.strip() for x in opts):
                st.error('Mavzu, savol va barcha 4 javob variantini kiriting.')
            elif len(set(x.strip().casefold() for x in opts))!=4:
                st.error('Javob variantlari bir-biridan farq qilishi kerak.')
            else:
                add_question(grade,section,subject,topic.strip(),prompt.strip(),[x.strip() for x in opts], 'ABCD'.index(answer),explanation.strip() or 'Izoh kiritilmagan.',task.strip() or 'Mavzuni takrorlang.')
                st.success('Savol saqlandi!')
    st.divider()
    st.subheader("📥 Savollarni ommaviy yuklash (CSV)")
    st.write("Savollar sonini o‘zingiz tanlaysiz: 5, 20, 100 yoki undan ko‘p. Excelda namunani ochib, har bir savolni alohida qatorga kiriting va CSV UTF-8 formatida saqlang. Sinf va fan yuqorida tanlanadi.")
    st.download_button("📄 CSV namunasini yuklab olish",csv_template(),
                       file_name="EDU_AI_savollar_namuna.csv",mime="text/csv")
    upload=st.file_uploader("Tayyor CSV faylni tanlang",type=["csv"],key=f"bulk_{grade}_{section}_{subject}")
    if upload is not None:
        try:
            parsed,problems=parse_bulk_csv(upload)
            if problems:
                st.error("Xatolar bor. Hech qanday savol yuklanmaydi.")
                for problem in problems[:30]: st.write("• "+problem)
            else:
                st.success(f"{len(parsed)} ta savol tekshiruvdan o‘tdi.")
                st.caption("Tasdiqlashdan keyin savollar mavjud bazaga qo‘shiladi; oldingilari o‘chirilmaydi. Juda katta fayllarni kichikroq CSV fayllarga bo‘lib yuklash mumkin.")
                if st.button(f"{len(parsed)} ta savolni bazaga saqlash",type="primary",key=f"confirm_{grade}_{section}_{subject}"):
                    insert_bulk_questions(grade,section,subject,parsed)
                    st.success(f"{len(parsed)} ta savol saqlandi!")
                    st.rerun()
        except ValueError as err:
            st.error(str(err))
    st.divider()
    questions=teacher_questions(grade,section,subject)
    st.subheader(f'Saqlangan savollar: {len(questions)} ta')
    for q in questions:
        with st.expander(f"#{q['id']} · {q['topic']} · {q['q'][:75]}"):
            st.write(q['q'])
            for i,opt in enumerate(q['opts']): st.write(f"{'ABCD'[i]}) {opt}" + (' ✓' if i==q['a'] else ''))
            st.caption('Izoh: '+q['why'])
            st.caption('Mashq: '+q['task'])
            if st.button('Savolni o‘chirish',key=f"delete_{q['id']}"):
                delete_question(q['id']); st.rerun()
    st.info('Hozircha savollarni tahrirlash uchun noto‘g‘ri savolni o‘chirib, yangisini kiriting.')

elif page == 'O‘qituvchi paneli':
    st.subheader('O‘quvchilar bo‘yicha alohida natijalar')
    with sqlite3.connect(DB) as con:
        if role=='admin':
            rows=con.execute('''SELECT a.id,s.grade,s.section,s.nickname,a.subject,a.created_at,a.score,a.total FROM attempts a JOIN students s ON s.id=a.student_id ORDER BY a.id DESC''').fetchall()
        else:
            rows=con.execute('''SELECT a.id,s.grade,s.section,s.nickname,a.subject,a.created_at,a.score,a.total FROM attempts a JOIN students s ON s.id=a.student_id ORDER BY a.id DESC''').fetchall()
    if not rows: st.info('Hali test natijalari yo‘q.')
    else:
        grades=sorted({r[1] for r in rows}); gradesel=st.selectbox('Sinf filtri',['Barchasi']+grades)
        subjects=st.selectbox('Fan filtri',['Barchasi']+SUBJECTS)
        filtered=[r for r in rows if (gradesel=='Barchasi' or r[1]==gradesel) and (subjects=='Barchasi' or r[4]==subjects)]
        st.metric('Test urinishlari',len(filtered))
        for aid,g,section,name,sub,date,score,total in filtered:
            with st.expander(f'{g}-{section} · {name} · {sub} · {date} · {score}/{total}'):
                with sqlite3.connect(DB) as con:
                    ts=con.execute('SELECT topic,correct,total FROM topic_results WHERE attempt_id=?',(aid,)).fetchall()
                for t,c,n in ts: st.write(f'{t}: {c}/{n} ({round(100*c/n)}%)')
        st.caption('Natijalar hisob roliga ko‘ra cheklangan.')
else:
    st.write('EDU AI 6.0 — sinflar, o‘quvchilar, fanlar va test natijalarini alohida yuritadigan namoyish dasturi.')
    st.write('Har bir o‘quvchi natijasi SQLite bazasida alohida ID bilan saqlanadi.')
    st.write('Fizika 7–11-sinflar, Informatika 5–11-sinflar uchun demo savollar mavjud. Matematika va tillar 1–11-sinflarda ishlaydi.')
    st.warning('Bu tanlov demosidir. Internetga joylashdan oldin xavfsizlik auditi, doimiy ma’lumotlar bazasi va maxfiylik nazorati talab etiladi.')
