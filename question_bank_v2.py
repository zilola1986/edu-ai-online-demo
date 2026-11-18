"""Namoyish savollari. Fan/sinf bo'yicha dastlabki kichik bank; rasmiy o'quv dasturi emas."""
# (savol, variantlar, javob indeksi, izoh, mashq)
BANK = {
"Informatika": {
"Python asoslari": [
("Python'da ekranga chiqarish funksiyasi qaysi?", ["print()", "input()", "int()", "len()"], 0, "print() qiymatni ekranga chiqaradi.", "print() yordamida 3 ta misol yozing."),
("Python'da butun son turi qaysi?", ["str", "int", "bool", "list"], 1, "int butun son turi.", "int va str ga 3 tadan misol keltiring.")],
"Algoritmlar": [
("Shart tekshiruvchi operator qaysi?", ["for", "if", "print", "import"], 1, "if shartni tekshiradi.", "Musbat sonni tekshiruvchi if yozing."),
("Takrorlash uchun qaysi operator ishlatiladi?", ["for", "def", "return", "pass"], 0, "for takrorlash operatori.", "1 dan 5 gacha chiqaruvchi sikl yozing.")],
"Sanoq sistemalari": [
("101₂ o'nlikda nechaga teng?", ["4", "5", "6", "7"], 1, "4 + 0 + 1 = 5.", "110₂ ni o'nlikka o'tkazing."),
("O'nlikdagi 2 soni ikkilikda qanday?", ["11", "10", "100", "01"], 1, "2 = 10₂.", "3, 4, 5 sonlarini ikkilikka o'tkazing.")]
},
"Matematika": {
"Arifmetika": [
("7 + 5 nechaga teng?", ["11", "12", "13", "14"], 1, "7 + 5 = 12.", "10 ta qo'shish mashqini bajaring."),
("6 × 4 nechaga teng?", ["20", "22", "24", "26"], 2, "6 × 4 = 24.", "6 ga ko'paytirish jadvalini takrorlang.")],
"Kasrlar": [
("1/2 + 1/2 nechaga teng?", ["1", "1/2", "2", "1/4"], 0, "Ikki yarim bir butunni tashkil etadi.", "Bir xil maxrajli 5 ta kasrni qo'shing."),
("3/4 kasrning maxraji qaysi?", ["3", "4", "7", "1"], 1, "Maxraj kasr chizig'i ostida bo'ladi.", "5 ta kasrning surat va maxrajini ajrating.")],
"Algebra": [
("x + 3 = 8 bo'lsa, x nechaga teng?", ["3", "4", "5", "6"], 2, "x = 8 − 3 = 5.", "5 ta sodda tenglamani yeching."),
("2x = 10 bo'lsa, x nechaga teng?", ["2", "3", "5", "10"], 2, "x = 10/2 = 5.", "Ko'paytma bilan bog'liq 5 tenglamani yeching.")]
},
"Fizika": {
"Harakat": [
("Tezlikning SI birligi qaysi?", ["m/s", "kg", "N", "J"], 0, "Tezlik m/s da o'lchanadi.", "Tezlik formulasi v=s/t bo'yicha 3 masala ishlang."),
("100 m yo'lni 20 s da bosib o'tgan jismning tezligi qancha?", ["2 m/s", "4 m/s", "5 m/s", "20 m/s"], 2, "v = 100/20 = 5 m/s.", "Masofa, vaqt, tezlikka doir 3 masala yeching.")],
"Kuch va energiya": [
("Kuchning SI birligi nima?", ["Joul", "Nyuton", "Vatt", "Paskal"], 1, "Kuch nyutonda (N) o'lchanadi.", "Kuch va massa birliklarini taqqoslang."),
("Ishning SI birligi nima?", ["Nyuton", "Vatt", "Joul", "Metr"], 2, "Mexanik ish joule (J) da o'lchanadi.", "Ish formulasini yozib, 2 misol yeching.")]
},
"Ingliz tili": {
"Lug'at": [
("'Apple' so'zining tarjimasi qaysi?", ["Olma", "Nok", "Uzum", "Shaftoli"], 0, "Apple — olma.", "Mevalar haqida 10 ta inglizcha so'z yozing."),
("'Book' so'zining tarjimasi qaysi?", ["Daftar", "Kitob", "Qalam", "Stol"], 1, "Book — kitob.", "Maktab buyumlaridan 10 ta so'z yodlang.")],
"Grammatika": [
("She ___ a student.", ["am", "is", "are", "be"], 1, "She bilan is ishlatiladi.", "To be bilan 5 ta gap tuzing."),
("I ___ football every day.", ["plays", "playing", "play", "played"], 2, "I bilan Present Simple'da play ishlatiladi.", "Present Simple'da 5 ta gap yozing.")]
},
"Rus tili": {
"Лексика": [
("«Книга» so'zining o'zbekcha tarjimasi qaysi?", ["Daftar", "Kitob", "Qalam", "Eshik"], 1, "Книга — kitob.", "Maktab mavzusida 10 ta ruscha so'z yodlang."),
("«Спасибо» so'zining tarjimasi qaysi?", ["Salom", "Xayr", "Rahmat", "Marhamat"], 2, "Спасибо — rahmat.", "5 ta odobli ruscha iborani yodlang.")],
"Грамматика": [
("«Я ___ ученик» gapidagi mos so'z qaysi?", ["есть", "—", "были", "будет"], 1, "Rus tilida hozirgi zamonda ot kesim oldida 'есть' odatda tushiriladi: Я — ученик.", "Я, ты, он bilan 3 ta sodda gap yozing."),
("«Они» olmoshi qaysi ma'noni bildiradi?", ["Men", "Sen", "U", "Ular"], 3, "Они — ular.", "Ruscha kishilik olmoshlarini takrorlang.")]
}
}

# Fizika 1-6 sinflarda alohida fan sifatida bu demoda taklif etilmaydi.
ELIGIBLE = {"Fizika": list(range(7,12))}

def questions_for(subject, grade):
    if subject in ELIGIBLE and grade not in ELIGIBLE[subject]:
        return []
    result=[]
    for topic, questions in BANK[subject].items():
        for prompt, options, answer, explanation, practice in questions:
            result.append({"topic":topic,"q":prompt,"opts":options,"a":answer,"why":explanation,"task":practice})
    return result
