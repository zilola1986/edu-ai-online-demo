from question_bank_v2 import questions_for as old_questions

SUBJECTS = ['Informatika','Matematika','Fizika','Ingliz tili','Rus tili']

def q(topic, prompt, answer, distractors, why, task):
    opts = [str(answer)] + [str(v) for v in distractors]
    return {'topic':topic,'q':prompt,'opts':opts,'a':0,'why':why,'task':task}

def questions_for(subject, grade):
    if subject == 'Fizika' and grade < 7:
        return []
    if subject == 'Informatika' and grade < 5:
        return []
    if subject == 'Matematika':
        # Demonstration questions are generated separately for every grade.
        if grade <= 4:
            a=grade*3+4; b=grade+3
            return [q('Qo‘shish',f'{a} + {b} = ?',a+b,[a+b+1,a+b-1,a+b+2],f'{a}+{b}={a+b}.','5 ta qo‘shish mashqini bajaring.'),
                    q('Ayirish',f'{a+b} − {b} = ?',a,[a+1,a-1,b],f'{a+b}−{b}={a}.','5 ta ayirish mashqini bajaring.'),
                    q('Ko‘paytirish',f'{grade+2} × 3 = ?',(grade+2)*3,[(grade+2)*3+1,(grade+2)*3-3,(grade+2)*3+3],'Ko‘paytirish takroriy qo‘shishdir.','Ko‘paytirish jadvalini takrorlang.')]
        if grade <= 6:
            n=grade+2
            return [q('Kasrlar','1/4 + 2/4 = ?','3/4',['1/2','2/8','1/4'],'Bir xil maxrajli kasrlarning suratlari qo‘shiladi.','5 ta kasrni qo‘shing.'),
                    q('Tenglama',f'x + {n} = {n+9}. x = ?',9,[8,10,n],f'x={n+9}−{n}=9.','5 ta tenglama yeching.'),
                    q('Foiz',f'{n*10} ning 10 foizi qancha?',n,[n+1,n*10,10],'10% — sonning o‘ndan bir qismi.','Foizga doir 5 ta masala yeching.')]
        n=grade+2
        return [q('Algebra',f'3x = {3*n}. x = ?',n,[n+1,n-1,3*n],f'x={3*n}/3={n}.','3 ta chiziqli tenglama yeching.'),
                q('Darajalar',f'{n}² = ?',n*n,[2*n,n*n+1,n*n-1],f'{n}²={n}×{n}.','Darajalarni hisoblashga oid 5 mashq bajaring.'),
                q('Funksiya',f'f(x)=2x+1. f({grade}) = ?',2*grade+1,[2*grade,grade+1,2*grade+2],'x o‘rniga berilgan sonni qo‘yamiz.','Funksiya qiymatiga oid 5 mashq bajaring.')]
    if subject == 'Ingliz tili':
        if grade <= 4:
            return [q('Lug‘at',"'Cat' so‘zining tarjimasi?",'Mushuk',['It','Qush','Ot'],'Cat — mushuk.','Hayvonlar haqida 5 so‘z o‘rganing.'),q('Lug‘at',"'Red' qanday rang?",'Qizil',['Ko‘k','Yashil','Sariq'],'Red — qizil.','Ranglarni takrorlang.'),q('Oddiy gap',"I ___ a pupil.",'am',['is','are','be'],'I bilan am ishlatiladi.','To be bilan 5 ta gap tuzing.')]
        if grade <= 7:
            return [q('Present Simple','She ___ to school every day.','goes',['go','going','gone'],'She bilan fe’lga -es qo‘shiladi.','Present Simple’da 5 gap yozing.'),q('Past Simple','Yesterday I ___ football.','played',['play','plays','playing'],'Yesterday o‘tgan zamonni bildiradi.','Past Simple’da 5 gap yozing.'),q('Lug‘at',"'Important' so‘zining tarjimasi?",'Muhim',['Oson','Kichik','Tez'],'Important — muhim.','5 ta yangi so‘z yozing.')]
        return [q('Conditionals','If I study, I ___ pass.','will',['would','am','was'],'First conditional: if + present, will + verb.','3 ta conditional gap tuzing.'),q('Passive Voice','The book ___ written in 2020.','was',['is','were','be'],'Past passive: was/were + V3.','Passive Voice’da 5 gap tuzing.'),q('Grammar','She has ___ finished her work.','already',['yesterday','tomorrow','ago'],'Already Present Perfect bilan ishlatiladi.','Present Perfect’ni takrorlang.')]
    if subject == 'Rus tili':
        if grade <= 4:
            return [q('Лексика','«Дом» so‘zining tarjimasi?','Uy',['Kitob','Daraxt','Suv'],'Дом — uy.','Uy haqida 5 ta so‘z yodlang.'),q('Лексика','«Мама» so‘zining tarjimasi?','Ona',['Ota','Aka','Opa'],'Мама — ona.','Oila haqida 5 so‘z yodlang.'),q('Числа','«Три» qaysi son?','3',['2','4','5'],'Три — uch.','1–10 sonlarni ruscha ayting.')]
        if grade <= 7:
            return [q('Лексика','«Школа» tarjimasi?','Maktab',['Uy','Bozor','Kutubxona'],'Школа — maktab.','Maktab haqida 5 gap yozing.'),q('Местоимения','«Мы» olmoshi qaysi?','Biz',['Siz','Ular','Men'],'Мы — biz.','Olmoshlarni takrorlang.'),q('Род','«Книга» qaysi rodda?','Женский',['Мужской','Средний','Общий'],'-а bilan tugagan книга — женский род.','Otlarning rodini aniqlang.')]
        return [q('Падежи','«Нет книги» birikmasida «книги» qaysi kelishik?','Родительный',['Именительный','Дательный','Винительный'],'Нет so‘zidan keyin родительный падеж keladi.','Kelishiklar bo‘yicha mashq bajaring.'),q('Глаголы','«Я читаю» qaysi zamon?','Настоящее',['Прошедшее','Будущее','Повелительное'],'Читаю hozirgi zamon.','Fe’l zamonlarini takrorlang.'),q('Лексика','«Образование» tarjimasi?','Ta’lim',['Tabiat','Sog‘liq','Mehnat'],'Образование — ta’lim.','Ta’lim mavzusida 5 gap yozing.')]
    # Other subjects retain the original question bank; mark these as shared demo questions.
    return old_questions(subject, grade)


def is_grade_specific(subject):
    return subject in {'Matematika','Ingliz tili','Rus tili'}
