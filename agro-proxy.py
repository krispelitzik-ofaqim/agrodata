# -*- coding: utf-8 -*-
"""AgroData local server + live-quote proxy (Yahoo Finance v8). Serves web/ and /api/quote."""
import http.server, socketserver, json, urllib.request, urllib.parse, time, threading, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
WEB  = os.path.join(HERE, "web")
PORT = int(os.environ.get("PORT", 8787))   # Render מזריק PORT; מקומית 8787
HOST = os.environ.get("HOST", "127.0.0.1") # באחסון נגדיר HOST=0.0.0.0
CACHE = {}; TTL = 60; LOCK = threading.Lock()

def fetch_symbol(sym):
    now = time.time()
    with LOCK:
        if sym in CACHE and now - CACHE[sym][0] < TTL:
            return CACHE[sym][1]
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(sym)}?interval=1d&range=1mo"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=10))
        res = d["chart"]["result"][0]; m = res["meta"]
        closes = [c for c in res["indicators"]["quote"][0]["close"] if c is not None]
        price = m.get("regularMarketPrice") or (closes[-1] if closes else None)
        prev  = m.get("chartPreviousClose") or m.get("previousClose") or (closes[-2] if len(closes) > 1 else price)
        out = {"symbol": sym, "price": price, "prev": prev, "series": closes[-24:], "currency": m.get("currency", "")}
    except Exception as e:
        out = {"symbol": sym, "error": str(e)[:100]}
    with LOCK:
        CACHE[sym] = (now, out)
    return out

OGCACHE = {}; OGTTL = 3600
def fetch_ogimage(u):
    now = time.time()
    with LOCK:
        if u in OGCACHE and now - OGCACHE[u][0] < OGTTL:
            return OGCACHE[u][1]
    img = None
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (compatible; AgroDataBot/1.0)"})
        raw = urllib.request.urlopen(req, timeout=10).read(500000).decode("utf-8", "ignore")
        pats = [r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)',
                r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
                r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)']
        for p in pats:
            m = re.search(p, raw, re.I)
            if m:
                img = urllib.parse.urljoin(u, m.group(1).replace("&amp;", "&")); break
    except Exception:
        img = None
    out = {"url": u, "image": img}
    with LOCK:
        OGCACHE[u] = (now, out)
    return out

GEMINI_KEY   = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
KB = (
 "== מי אנחנו ==\n"
 "AgroData (Ofakim AgroData Center) = זירת האגרו-טק של ישראל, מרכז נתונים+מחקר+ידע חקלאי, שבסיסו בעיר אופקים שבנגב (״בירת האגרו-טק של ישראל״). מנועים: מאגר נתונים (AgroLake), אנליטיקת AI (AgroMind), חדשות (AgroPulse), מחקר (AgroScholar), חיישנים, מפות (AgroMap), חברות (AgroDirectory), כתבי עת (AgroLibrary), כנסים (AgroExpo), סחר בינלאומי (AgroTrade), המדען הראשי וחממות (AgroLabs), מו״פים (AgroRnD), חינוך וקהילה. זירה פיננסית: AgroBank/Invest/Stock (מדדים חיים מ-Yahoo)/Venture/Launch/Capital.\n"
 "== חברות אגרו-טק ישראליות (לפי תחום ומה עושות) ==\n"
 "השקיה ומים: נטפים (חלוצת הטפטוף, קיבוץ חצרים, #1 עולמי), Rivulis, NaanDanJain, N-Drip (טפטוף בכוח הכובד), SupPlant (השקיה מבוססת AI), Manna, Amiad (סינון מים), Bermad (שסתומים). "
 "חישה וחקלאות מדייקת: CropX (חיישני קרקע), Phytech (ניטור צמח), Prospera/Valmont (AI לגידולים), Taranis (הדמיה אווירית), SeeTree (מטעים), Agritask, Agmatix/ICL, Saturas (חיישן גזע), Viridix. "
 "רובוטיקה ואוטומציה: Tevel (רחפני קטיף), FFRobotics (רובוט קטיף), Metomotion (רובוט חממות), Blue White Robotics (טרקטור אוטונומי), Greeneye (ריסוס מדייק AI), Fieldin, BeeHero+Beewise (האבקה/כוורת רובוטית), Edete. "
 "זרעים וגנטיקה: Evogene (ביולוגיה חישובית), Equinom (השבחה לחלבון), Hazera, Rahan Meristem, Salicrop, Kaiima. "
 "דשן והגנת הצומח: ICL (דשנים, אשלג, ים המלח), ADAMA (הגנת הצומח), Haifa Group (ניטרט), Groundwork BioAg (מיקוריזה). "
 "פוד-טק וחלבון חלופי: Aleph Farms + Believer Meats (בשר מתורבת), Redefine Meat (בשר צמחי בהדפסת 3D), Remilk+Imagindairy (חלב מתסיסה), Steakholder, InnovoPro (חלבון חומוס). "
 "חקלאות ימית: AquaMaof, BioFishency. עירונית/אנכית: Vertical Field, Growee.\n"
 "== מוסדות מחקר ואקדמיה ==\n"
 "מכון ויצמן (רחובות), הפקולטה לחקלאות מזון וסביבה ע״ש רוברט סמית (רחובות, האונ׳ העברית), אוניברסיטת בן-גוריון (מכוני בלאושטיין, שדה בוקר), מכון וולקני/ARO (ראשל״צ, זרוע המחקר של משרד החקלאות), מיג״ל (קרית שמונה), הטכניון, אונ׳ ת״א, מו״פ ערבה, מו״פ רמת נגב, מו״פ צפון.\n"
 "== המדען הראשי וחממות ==\n"
 "רשות החדשנות (לשעבר לשכת המדען הראשי) + המדען הראשי במשרד החקלאות. חממות אגרי-פוד-טק: Fresh Start (פוד-טק, קרית שמונה, שותפים תנובה/טמפו), The Kitchen (שטראוס, אשדוד), Trendlines Agrifood (מסגב), Millennium Food-Tech (ת״א), Arava Innovation (ערבה), Capital Nature, Incubit (אלביט), NGT3 (נצרת).\n"
 "== החלטות ממשלה רלוונטיות ==\n"
 "החלטה 207 (רפורמה בחקלאות והוזלת יוקר מחיה), 2397 (פיתוח הנגב), 3079 (מו״פ חקלאי וחממות), 542 (מים לחקלאות), 4028 (ביטחון תזונתי ומאגר נתונים), חוק הגנת הפרטיות (תיקון 13), 1145 (עידוד יצוא), data.gov.il (נתונים פתוחים).\n"
 "== סחר בינלאומי ==\n"
 "יצוא חקלאי ~$2.4B/שנה (תמרים #1 עולמי, פלפל, אבוקדו, עגבניות שרי, פרחים, עשבי תיבול, הדרים; שוק עיקרי EU). יבוא ~$6.1B (חיטה, תירס, סויה, בשר, קפה). מאזן שלילי ~$3.7B.\n"
 "== עובדות מפתח ==\n"
 "ישראל מובילה עולמית בהשקיה בטפטוף ובחקלאות מדבר. ~700 חברות אגריפוד-טק פעילות. אופקים והנגב = לב מתפתח של חדשנות חקלאית.")
def build_prompt(q):
    return ("אתה AgroMind, מנוע הידע של זירת האגרו-טק AgroData. ענה בעברית תשובה מלאה, מפורטת ומובנית (פתיח קצר ואז נקודות/פסקאות). "
            "בסס את התשובה בעיקר על מאגר הזירה שלהלן, והוסף ידע מקצועי עדכני היכן שרלוונטי. אל תפתח את התשובה במילים ׳כ-AgroMind׳ — ענה ישירות לעניין. ציין חברות, מוסדות ונתונים ספציפיים מהמאגר. אל תמציא.\n\n=== מאגר הזירה ===\n" + KB + "\n\n=== שאלת המשתמש ===\n" + q)

ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5")
def ask_claude(q):
    if not ANTHROPIC_KEY:
        return {"answer": "מנוע Claude אינו מחובר. הגדר ANTHROPIC_API_KEY והפעל מחדש.", "demo": True}
    body = json.dumps({"model": ANTHROPIC_MODEL, "max_tokens": 1600,
                       "messages": [{"role": "user", "content": build_prompt(q)}]}).encode("utf-8")
    last = ""
    for attempt in range(2):
        req = urllib.request.Request("https://api.anthropic.com/v1/messages", data=body,
                                     headers={"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        try:
            d = json.load(urllib.request.urlopen(req, timeout=120))
            txt = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text").strip()
            return {"answer": txt or "—", "demo": False, "model": ANTHROPIC_MODEL, "engine": "claude"}
        except Exception as e:
            last = str(getattr(e, "code", "")) or type(e).__name__
    return {"answer": "שגיאת חיבור ל-Claude (" + last + "). ודא שהמפתח תקין ושיש קרדיטים.", "demo": True}

def ask_gemini(q):
    if not GEMINI_KEY:
        return {"answer": "מנוע ה-AI עדיין לא מחובר. הגדר משתנה סביבה GEMINI_API_KEY והפעל מחדש את השרת.", "demo": True}
    prompt = build_prompt(q)
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + GEMINI_MODEL + ":generateContent?key=" + GEMINI_KEY
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048, "thinkingConfig": {"thinkingBudget": 0}}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=30))
        txt = d["candidates"][0]["content"]["parts"][0]["text"]
        return {"answer": txt.strip(), "demo": False, "model": GEMINI_MODEL, "engine": "gemini"}
    except Exception as e:
        code = getattr(e, "code", None)
        if code == 429:
            msg = "מנוע ה-AI זמנית אינו זמין (המכסה נגמרה או שאין דרגה חינמית לפרויקט). לחיבור מלא נדרש מפתח Gemini עם חשבון חיוב פעיל."
        elif code in (401, 403):
            msg = "בעיית הרשאה — ודא שמפתח ה-Gemini תקין ושה-Generative Language API מופעל בפרויקט."
        else:
            msg = "שגיאת חיבור זמנית למנוע ה-AI. נסו שוב בעוד רגע."
        return {"answer": msg, "demo": True, "err": code}

class H(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=WEB, **k)
    def log_message(self, *a): pass
    def do_GET(self):
        if self.path.startswith("/api/quote"):
            q = urllib.parse.urlparse(self.path).query
            syms = urllib.parse.parse_qs(q).get("symbols", [""])[0].split(",")
            syms = [s for s in syms if s]
            out = [None]*len(syms); ths = []
            def work(i, s): out[i] = fetch_symbol(s)
            for i, s in enumerate(syms):
                t = threading.Thread(target=work, args=(i, s)); t.start(); ths.append(t)
            for t in ths: t.join()
            body = json.dumps([o for o in out if o]).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/ask"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            q = qs.get("q", [""])[0]; eng = qs.get("engine", ["gemini"])[0]
            if not q.strip(): out = {"answer": "נא להזין שאלה.", "demo": True}
            elif eng == "claude": out = ask_claude(q)
            else: out = ask_gemini(q)
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/ogimage"):
            q = urllib.parse.urlparse(self.path).query
            u = urllib.parse.parse_qs(q).get("url", [""])[0]
            out = fetch_ogimage(u) if u else {"image": None}
            body = json.dumps(out).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        return super().do_GET()

socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer((HOST, PORT), H) as httpd:
    print(f"AgroData live server → http://localhost:{PORT}/agro-stock.html")
    httpd.serve_forever()
