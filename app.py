import base64
from pathlib import Path
from collections import defaultdict
import streamlit as st
from question_bank import SUBJECTS, questions_for, is_grade_specific

st.set_page_config(page_title="EDU AI — Onlayn demo", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")
image_file = Path(__file__).with_name("edu_ai_background.jpg")
background = base64.b64encode(image_file.read_bytes()).decode("ascii") if image_file.exists() else ""
# CSS is a plain string to avoid accidental Python f-string brace interpretation.
css = """<style>
[data-testid="stAppViewContainer"] {background-image:linear-gradient(rgba(255,255,255,.88),rgba(255,255,255,.88)),url('data:image/jpeg;base64,__BG__');background-size:cover;background-position:center;background-attachment:fixed;}
[data-testid="stSidebar"] {background:linear-gradient(180deg,#102445,#21477a);}
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2 {color:#fff;}
[data-testid="stSidebar"] label {color:#fff;}
[data-testid="stForm"] {background:rgba(255,255,255,.93);padding:1.2rem;border-radius:16px;border:1px solid #dce7f3;}
.block-container {max-width:1100px;padding-top:2rem;}
</style>""".replace("__BG__", background)
st.markdown(css,unsafe_allow_html=True)

st.sidebar.title("🎓 EDU AI")
st.sidebar.caption("TANLOV UCHUN OCHIQ DEMO")
page = st.sidebar.radio("Bo‘limlar", ["🏠 Bosh sahifa","📝 Demo test","📊 Natijam","ℹ️ Loyiha haqida"])
st.sidebar.info("🔒 Bu demo haqiqiy foydalanuvchi ma’lumotlarini yig‘maydi. Natijalar faqat ochiq brauzer sessiyasida saqlanadi.")

if page == "🏠 Bosh sahifa":
    st.title("🎓 EDU AI — Aqlli ta’lim yordamchisi")
    st.subheader("Raqamli avlod qizlari tanlovi uchun namoyish")
    st.write("Fan va sinfni tanlang, qisqa testni bajaring hamda mavzular bo‘yicha tahlilni ko‘ring.")
    a,b,c=st.columns(3)
    a.metric("Fanlar",len(SUBJECTS));b.metric("Sinflar",11);c.metric("Demo", "Ochiq")
    st.success("Chap menyudan «📝 Demo test» bo‘limini tanlang.")
    st.caption("Bu ochiq demo: o‘qituvchi paneli, parollar va haqiqiy o‘quvchilar bazasi internetga chiqarilmagan.")
elif page == "📝 Demo test":
    st.title("📝 Demo test")
    a,b,c=st.columns(3)
    subject=a.selectbox("Fan",SUBJECTS)
    grade=b.selectbox("Sinf",list(range(1,12)),index=8,format_func=lambda v:f"{v}-sinf")
    bank=questions_for(subject,grade)
    count=c.number_input("Savollar soni",min_value=1,max_value=max(1,len(bank)),value=min(5,max(1,len(bank))))
    questions=bank[:int(count)]
    if not bank:
        st.warning("Bu fan va sinf uchun demo savollar mavjud emas.")
    else:
        st.caption("Savollar namunaviy. Test natijalari doimiy bazaga yozilmaydi.")
        with st.form(f"quiz_{subject}_{grade}_{count}"):
            answers=[]
            for i,q in enumerate(questions):
                st.markdown(f"**{i+1}. [{q['topic']}] {q['q']}**")
                answers.append(st.radio("Javob",q['opts'],index=None,key=f"answer_{subject}_{grade}_{count}_{i}",label_visibility="collapsed"))
                st.divider()
            submit=st.form_submit_button("Natijani ko‘rish",type="primary")
        if submit:
            if any(a is None for a in answers):
                st.warning("Barcha savollarga javob bering.")
            else:
                totals=defaultdict(int);correct=defaultdict(int);wrong=[];score=0
                for q,ans in zip(questions,answers):
                    totals[q['topic']]+=1
                    if ans==q['opts'][q['a']]:
                        score+=1;correct[q['topic']]+=1
                    else:wrong.append(q)
                st.session_state['last_result']={'subject':subject,'grade':grade,'score':score,'total':len(questions),'topics':{k:(correct[k],v) for k,v in totals.items()},'wrong':wrong}
                st.success("Natija hisoblandi! «📊 Natijam» bo‘limini oching.")
                st.metric("To‘g‘ri javoblar",f"{score}/{len(questions)}")
elif page == "📊 Natijam":
    st.title("📊 Test natijasi")
    result=st.session_state.get('last_result')
    if not result:
        st.info("Avval «📝 Demo test» bo‘limida testni bajaring.")
    else:
        st.subheader(f"{result['grade']}-sinf · {result['subject']}")
        pct=round(100*result['score']/result['total'])
        a,b=st.columns(2)
        a.metric("To‘g‘ri javob",f"{result['score']}/{result['total']}")
        b.metric("Natija",f"{pct}%")
        st.subheader("Mavzular bo‘yicha tahlil")
        for topic,(correct,total) in result['topics'].items():
            p=round(100*correct/total)
            st.write(f"**{topic}: {p}%**")
            st.progress(p/100)
        if result['wrong']:
            with st.expander("Noto‘g‘ri javoblar va tavsiyalar"):
                for q in result['wrong']:
                    st.write(f"**{q['q']}**")
                    st.write("To‘g‘ri javob: "+str(q['opts'][q['a']]))
                    st.caption(q.get('why',''))
                    st.write("Tavsiya: "+q.get('task','Mavzuni takrorlang.'))
        else:st.success("Barcha savollar to‘g‘ri!")
else:
    st.title("ℹ️ EDU AI haqida")
    st.write("EDU AI — Python va Streamlit asosida yaratilgan ta’limiy diagnostika prototipi.")
    st.write("U test javoblarini tekshiradi, mavzular bo‘yicha natijalarni hisoblaydi va oldindan yozilgan tavsiyalarni ko‘rsatadi.")
    st.warning("Hozirgi demo o‘qitilgan sun’iy intellekt modelidan foydalanmaydi. AI asosidagi individual tavsiyalar kelgusi rivojlanish bosqichi.")
    st.write("Maxfiy ma’lumotlar, loginlar va haqiqiy o‘quvchi natijalari bu ochiq demo tarkibiga kiritilmagan.")
