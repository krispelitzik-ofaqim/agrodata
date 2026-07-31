# העלאת AgroData לאוויר + חיבור הדומיין agrodata.co.il

הכל מוכן לפריסה. השרת (`agro-proxy.py`) מגיש את `web/` **וגם** את הדאטה החי (Yahoo, og-images).
כבר הוכן: `HOST`/`PORT` מהסביבה + `render.yaml` + `Procfile` + `requirements.txt`.

---

## שלב 1 — להעלות את הקוד ל-GitHub (חד-פעמי)
```
cd ~/Desktop/agrodata
git init && git add . && git commit -m "AgroData"
```
צור ריפו חדש ב-github.com (למשל `agrodata`) ואז:
```
git remote add origin https://github.com/<USERNAME>/agrodata.git
git branch -M main && git push -u origin main
```

## שלב 2 — לפרוס ב-Render (יש לך חשבון)
1. render.com → **New → Web Service** → חבר את ריפו `agrodata`.
2. Render יזהה את `render.yaml` אוטומטית. אם לא:
   - Runtime: **Python**
   - Build Command: `echo no-deps`
   - Start Command: `python3 agro-proxy.py`
   - Environment: `HOST = 0.0.0.0`
3. Deploy. תקבל כתובת כמו `https://agrodata.onrender.com` — **בדוק שהכל עובד שם** (כולל אגרו-סטוק חי).

## שלב 3 — לחבר את הדומיין agrodata.co.il (כשאושר ב-LiveDNS)
1. ב-Render: **Settings → Custom Domains → Add** → הקלד `agrodata.co.il` (וגם `www.agrodata.co.il`).
2. Render יראה לך יעד DNS (IP ל-A record, ו-CNAME ל-www). העתק אותם.
3. ב-**LiveDNS** (ניהול הדומיין) → הוסף רשומות:
   - `A` · שם `@` · ערך = ה-IP ש-Render נתן
   - `CNAME` · שם `www` · ערך = `agrodata.onrender.com`
4. המתן להתפשטות DNS (דקות עד שעות). Render מנפיק **HTTPS** אוטומטית.

---

## חלופה מהירה (בלי דאטה חי) — אתר סטטי
אם רוצים רק את האתר (אגרו-סטוק יציג דמו): Render → **New → Static Site** → Publish directory = `web`. חיבור הדומיין זהה לשלב 3.

## הערות
- הדומיין `agrodata.co.il` עדיין **בהליכי אישור** ב-LiveDNS — שלב 3 רק אחרי שהוא מופיע בממשק.
- `agrodata.ai` (גלובלי) — לתפוס בהמשך ב-GoDaddy ולהפנות לאותו שירות.
- לוח הניהול הפנימי: `/(...)/admin.html` — מומלץ להגן בסיסמה לפני עלייה לאוויר (Render → Environment / Basic Auth).
