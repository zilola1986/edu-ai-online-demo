# EDU AI 6.0 — Hakamlar uchun Streamlit demo

## GitHub / Streamlit Community Cloud
1. Eski GitHub repozitoriyangizdagi loyiha fayllarini ushbu papkadagi fayllar bilan almashtiring. `STREAMLIT_SECRETS_NAMUNA.toml` faqat namuna; haqiqiy parollarni unga yozib GitHub'ga yubormang.
2. Streamlit Cloud ilovasida **Settings → Secrets** bo‘limiga namuna fayldagi kalitlarni kiriting va haqiqiy maxfiy qiymatlarni o‘rnating.
3. App entrypoint: `app.py`. `requirements.txt` avtomatik o‘qiladi.
4. Demo loginlar: `admin_demo`, `teacher_demo`, `student_demo`; parollar Secrets'dagi `[demo_accounts]` qiymatlaridir.
5. Demo sinfi: 9-A; `Demo-oquvchi-01` avtomatik yaratiladi.

## Muhim
- Birinchi tashrif buyurgan odam administrator yaratolmaydi. Uchta demo hisob faqat maxfiy sozlamalar kiritilganda yaratiladi.
- Demo hisoblar SQLite bazasi bo‘shatilganda qayta yaratiladi. **Keyin qo‘shilgan hisoblar, test natijalari va savollar doimiy saqlanmaydi.** Server qayta ishga tushishi ma'lumotlarni yo‘qotishi mumkin.
- Secrets'dagi parollarni almashtirish mavjud SQLite hisoblarining parolini avtomatik almashtirmaydi. Buning uchun ilovadagi parol yangilash funksiyasidan foydalaning yoki ma’lumotlar bazasini qayta yarating.
- Hakamlar bilan faqat sun’iy ma’lumotlar ishlating. Admin hisobiga kirgan odam boshqa hisoblar va savollarni o‘zgartira oladi. Ommaviy havolada admin parolini cheklanmagan auditoriyaga tarqatmang.
- GitHub'ga `edu_ai_v5.db`, `.streamlit/secrets.toml`, `.env`, API kaliti yoki haqiqiy parollarni joylamang.
