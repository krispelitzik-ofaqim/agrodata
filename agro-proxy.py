# -*- coding: utf-8 -*-
"""AgroData local server + live-quote proxy (Yahoo Finance v8). Serves web/ and /api/quote."""
import http.server, socketserver, json, urllib.request, urllib.parse, time, threading, os, re, base64, datetime, concurrent.futures

HERE = os.path.dirname(os.path.abspath(__file__))
WEB  = os.path.join(HERE, "web")
PORT = int(os.environ.get("PORT", 8787))   # Render מזריק PORT; מקומית 8787
HOST = os.environ.get("HOST", "127.0.0.1") # באחסון נגדיר HOST=0.0.0.0
CACHE = {}; TTL = 60; LOCK = threading.Lock()

# ---- native discussion board (name + message, no login) ----
COMMENTS_FILE = os.path.join(os.environ.get("DATA_DIR", HERE), "comments.json")
CLOCK = threading.Lock()
def load_comments():
    try:
        with open(COMMENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []
def save_comments(items):
    with open(COMMENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False)
APPS_FILE = os.path.join(os.environ.get("DATA_DIR", HERE), "applications.json")
def save_application(data):
    rec = {}
    for k in ("name", "email", "phone", "role", "linkedin", "company", "website", "sector",
              "stage", "founded", "location", "about", "problem", "amount", "valuation",
              "use", "instrument", "equity", "shares", "notes"):
        rec[k] = str(data.get(k, ""))[:2000]
    f = data.get("file")
    if isinstance(f, dict) and f.get("data"):
        try:
            m = re.match(r"data:[^;]+;base64,(.+)$", f.get("data"), re.S)
            if m:
                raw = base64.b64decode(m.group(1))
                if len(raw) <= 8 * 1024 * 1024:
                    updir = os.path.join(WEB, "uploads", "apply")
                    os.makedirs(updir, exist_ok=True)
                    ext = re.sub(r"[^a-zA-Z0-9]", "", (f.get("name", "file").rsplit(".", 1) + ["bin"])[-1])[:5] or "bin"
                    fn = "app" + str(int(time.time())) + "_" + os.urandom(4).hex() + "." + ext
                    with open(os.path.join(updir, fn), "wb") as fh:
                        fh.write(raw)
                    rec["file"] = "uploads/apply/" + fn
                    rec["file_name"] = str(f.get("name", ""))[:120]
        except Exception:
            pass
    rec["ts"] = int(time.time())
    with CLOCK:
        try:
            items = json.load(open(APPS_FILE, encoding="utf-8"))
        except Exception:
            items = []
        items.append(rec)
        json.dump(items, open(APPS_FILE, "w", encoding="utf-8"), ensure_ascii=False)
    return rec

# ---- AgroInvest crowdfunding ----
CAMP_FILE = os.path.join(os.environ.get("DATA_DIR", HERE), "campaigns.json")
def load_campaigns():
    try:
        return json.load(open(CAMP_FILE, encoding="utf-8"))
    except Exception:
        return None
def save_campaigns(items):
    json.dump(items, open(CAMP_FILE, "w", encoding="utf-8"), ensure_ascii=False)
def seed_campaigns():
    now = int(time.time()); day = 86400
    seed = [
     {"id":"c_solar","title":"חממה סולארית חכמה לנגב","cat":"אנרגיה וסביבה","owner":"אגרו-סולאר בע\"מ",
      "tagline":"חממה אוטונומית שמייצרת את החשמל שלה ומגדלת ירקות כל השנה במים ממוחזרים.",
      "story":"פיילוט באופקים: חממה 1,000 מ\"ר עם פאנלים דו-פנים, בקרת אקלים AI והשקיה במחזור סגור. המטרה — 40% חיסכון אנרגיה ופי-3 יבול. הכספים ישמשו להקמת החממה הראשונה ולניטור שנה מלאה.",
      "image":"https://loremflickr.com/800/500/greenhouse,solar/all","video":"OYcfk03NBcs",
      "goal":250000,"raised":168400,"backers":214,"deadline":now+18*day,"contact":"solar@agro.il",
      "rewards":[{"amount":100,"title":"תומך","desc":"עדכונים מהשטח + שם בעמוד התודות"},
                 {"amount":500,"title":"שותף","desc":"סל ירקות מהקציר הראשון + סיור בחממה"},
                 {"amount":2500,"title":"משקיע-מייסד","desc":"תג מייסד, ביקור VIP ודו\"ח תוצאות מלא"}]},
     {"id":"c_drone","title":"רחפן ניטור מחלות לגד\"ש","cat":"רחפנים ו-AI","owner":"SkyAgro",
      "tagline":"רחפן שמזהה מחלות ומזיקים 10 ימים לפני העין האנושית, וחוסך ריסוס מיותר.",
      "story":"מצלמה מולטי-ספקטרלית + מודל AI שסורק שדות ומתריע נקודתית. גיוס לפיתוח הדור הבא ולפיילוט אצל 20 מגדלים.",
      "image":"https://loremflickr.com/800/500/drone,field/all","video":"","goal":180000,"raised":92300,"backers":131,
      "deadline":now+27*day,"contact":"fly@skyagro.il",
      "rewards":[{"amount":150,"title":"חבר קהילה","desc":"גישה מוקדמת לדוחות הניטור"},
                 {"amount":1000,"title":"מגדל-פיילוט","desc":"סריקת שדה חינם לעונה שלמה"}]},
     {"id":"c_algae","title":"חוות אצות ספירולינה עירונית","cat":"פוד-טק","owner":"BlueGreen Foods",
      "tagline":"חלבון-על בר-קיימא מגדלים באמצע העיר, בפוטוביוריאקטורים קומפקטיים.",
      "story":"מערכת מודולרית לגידול ספירולינה טרייה לצריכה מקומית — ללא קרקע וכמעט ללא מים. הכספים להרחבת קו הייצור.",
      "image":"https://loremflickr.com/800/500/algae,green/all","video":"","goal":120000,"raised":120000,"backers":298,
      "deadline":now+5*day,"contact":"hello@bluegreen.il",
      "rewards":[{"amount":80,"title":"טועם","desc":"אריזת ספירולינה טרייה"},
                 {"amount":600,"title":"מאמץ","desc":"מנוי חודשי לשנה + סדנת תזונה"}]},
     {"id":"c_robot","title":"רובוט קטיף אוטונומי לחממות","cat":"רובוטיקה","owner":"HarvestBot",
      "tagline":"זרוע רובוטית עם ראייה ממוחשבת שקוטפת עגבניות ופלפלים 24/7 — פותרת את מחסור העובדים.",
      "story":"מחסור חמור בידיים עובדות מייקר את התוצרת. הרובוט שלנו מזהה פרי בשל, קוטף בעדינות וממיין — בעלות של שליש מעבודת אדם. הגיוס למימון 5 רובוטים לפיילוט אצל מגדלים בבשור ובערבה.",
      "image":"https://loremflickr.com/800/500/robot,greenhouse/all","video":"","goal":320000,"raised":141200,"backers":176,
      "deadline":now+22*day,"contact":"team@harvestbot.il",
      "rewards":[{"amount":120,"title":"עוקב","desc":"עדכוני פיתוח + סרטוני קטיף"},
                 {"amount":1800,"title":"מגדל-פיילוט","desc":"עדיפות בתור לפיילוט + הדרכה"}]},
     {"id":"c_seeds","title":"בנק זרעי מורשת קהילתי","cat":"זרעים וגנטיקה","owner":"עמותת זרעי הארץ",
      "tagline":"שימור זני ירקות ותבלינים מקומיים בסכנת הכחדה — בנק זרעים פתוח לקהילה.",
      "story":"עשרות זני מורשת נעלמים. אנו אוספים, מרבים ומחלקים זרעים פתוחי-האבקה לחקלאים ולגננים, עם מאגר ידע דיגיטלי. הכספים להקמת חדר קירור, מעבדת נביטה ופלטפורמת שיתוף.",
      "image":"https://loremflickr.com/800/500/seeds,vegetables/all","video":"","goal":90000,"raised":38700,"backers":163,
      "deadline":now+34*day,"contact":"seeds@zeraim.il",
      "rewards":[{"amount":60,"title":"גנן","desc":"ערכת 5 זני מורשת לגינה"},
                 {"amount":360,"title":"שומר זרעים","desc":"ערכה מורחבת + סדנת ריבוי זרעים"}]},
     {"id":"c_vertical","title":"חוות ירק אנכית עירונית","cat":"חקלאות עירונית","owner":"UrbanGreens",
      "tagline":"עלים טריים גדלים בלב העיר, קרוב לצרכן, בלי קרקע וכמעט בלי מים.","story":"מדפי גידול הידרופוניים בקומות עם תאורת LED חכמה. הכספים להקמת חוות הדגל הראשונה.",
      "image":"https://loremflickr.com/800/500/vertical,farm/all","video":"","goal":140000,"raised":51000,"backers":88,"deadline":now+29*day,"contact":"u@urbangreens.il",
      "rewards":[{"amount":70,"title":"תומך","desc":"סל עלים טרי"},{"amount":500,"title":"שותף","desc":"מנוי חודשי + סיור"}]},
     {"id":"c_bee","title":"כוורות חכמות לדבש הנגב","cat":"אנרגיה וסביבה","owner":"BeeSmart",
      "tagline":"חיישנים שמנטרים את בריאות הכוורת ומגדילים תנובת דבש ב-30%.","story":"מערכת ניטור IoT לכוורתנים — טמפרטורה, משקל ורעש. גיוס להרחבה ל-200 כוורות.",
      "image":"https://loremflickr.com/800/500/bee,honey/all","video":"","goal":75000,"raised":41800,"backers":142,"deadline":now+16*day,"contact":"b@beesmart.il",
      "rewards":[{"amount":90,"title":"אוהב דבש","desc":"צנצנת דבש נגב"},{"amount":450,"title":"מאמץ כוורת","desc":"כוורת על שמך + דבש שנתי"}]},
     {"id":"c_water","title":"בקרת השקיה חכמה מבוססת AI","cat":"השקיה ומים","owner":"AquaMind",
      "tagline":"אלגוריתם שמחליט מתי וכמה להשקות — חיסכון של 35% מים ויבול גבוה יותר.","story":"חיבור לחיישני קרקע ותחזית מזג אוויר. גיוס לפיתוח והרחבת פיילוטים.",
      "image":"https://loremflickr.com/800/500/irrigation,water/all","video":"","goal":200000,"raised":77500,"backers":109,"deadline":now+31*day,"contact":"a@aquamind.il",
      "rewards":[{"amount":110,"title":"עוקב","desc":"גישה מוקדמת לאפליקציה"},{"amount":1200,"title":"מגדל-פיילוט","desc":"התקנה חינם לחלקה"}]},
     {"id":"c_mush","title":"חוות פטריות גורמה","cat":"פוד-טק","owner":"FungiFarm",
      "tagline":"פטריות מאכל מיוחדות (שיטאקה, צדפה, רעמת האריה) בגידול מבוקר מקומי.","story":"מצע גידול ממחזור פסולת חקלאית. גיוס להקמת חדרי גידול ומעבדה.",
      "image":"https://loremflickr.com/800/500/mushroom,farm/all","video":"","goal":85000,"raised":29400,"backers":74,"deadline":now+25*day,"contact":"m@fungifarm.il",
      "rewards":[{"amount":75,"title":"טועם","desc":"סל פטריות טרי"},{"amount":420,"title":"מגדל ביתי","desc":"ערכת גידול ביתית + ליווי"}]},
     {"id":"c_olive","title":"שיקום כרם זיתים עתיק","cat":"כללי","owner":"משפחת אבו-חמד",
      "tagline":"החייאת מטע זיתים בן 300 שנה והפקת שמן זית כתית מעולה.","story":"גיזום, השקיה ובית בד קהילתי. הכספים לשיקום העצים ולציוד הפקה.",
      "image":"https://loremflickr.com/800/500/olive,tree/all","video":"","goal":65000,"raised":52100,"backers":211,"deadline":now+9*day,"contact":"o@olivefarm.il",
      "rewards":[{"amount":85,"title":"אוהב שמן","desc":"בקבוק שמן זית מהבציר"},{"amount":390,"title":"מאמץ עץ","desc":"עץ על שמך + שמן שנתי"}]},
     {"id":"c_fish","title":"אקוופוניקה קהילתית","cat":"פוד-טק","owner":"AquaLoop",
      "tagline":"מערכת שמגדלת דגים וירקות יחד במחזור מים סגור, לקהילה עירונית.","story":"חממת אקוופוניקה חינוכית-מסחרית. גיוס להקמה ולתוכנית חינוכית.",
      "image":"https://loremflickr.com/800/500/aquaponics,fish/all","video":"","goal":110000,"raised":33600,"backers":91,"deadline":now+37*day,"contact":"a@aqualoop.il",
      "rewards":[{"amount":95,"title":"חבר","desc":"סל ירקות + סיור"},{"amount":550,"title":"שותף","desc":"שם על הקיר + סדנה"}]},
     {"id":"c_past","title":"מייבש שמש לתוצרת חקלאית","cat":"אנרגיה וסביבה","owner":"SunDry",
      "tagline":"ייבוש פירות וירקות באנרגיית שמש — הארכת חיי מדף בלי חשמל.","story":"קמפיין שהסתיים ולא הגיע ליעד — דוגמה לסטטוס ׳לא הצליח׳.",
      "image":"https://loremflickr.com/800/500/dried,fruit/all","video":"","goal":100000,"raised":42000,"backers":97,
      "deadline":now-4*day,"contact":"s@sundry.il",
      "rewards":[{"amount":80,"title":"תומך","desc":"חבילת פירות מיובשים"}]}]
    save_campaigns(seed); return seed
def list_campaigns():
    items = load_campaigns()
    if items is None:
        items = seed_campaigns()
    now = int(time.time())
    out = []
    for c in items:
        d = dict(c)
        goal = max(1, int(c.get("goal", 1)))
        d["pct"] = min(100, round(int(c.get("raised", 0)) * 100 / goal))
        left = int(c.get("deadline", now)) - now
        d["daysleft"] = max(0, left // 86400)
        d.pop("contact", None)
        out.append(d)
    out.sort(key=lambda x: x.get("pct", 0), reverse=True)
    return {"items": out}
def create_campaign(data):
    items = load_campaigns()
    if items is None:
        items = seed_campaigns()
    img = data.get("image")
    imgpath = ""
    if isinstance(img, str) and img.startswith("data:"):
        imgpath = save_image(img) or ""
    elif isinstance(img, str):
        imgpath = img[:400]
    try:
        goal = max(1000, min(5000000, int(float(data.get("goal") or 0))))
    except Exception:
        goal = 50000
    try:
        days = max(1, min(120, int(float(data.get("days") or 30))))
    except Exception:
        days = 30
    rewards = []
    for r in (data.get("rewards") or [])[:6]:
        try:
            rewards.append({"amount": int(float(r.get("amount") or 0)),
                            "title": str(r.get("title", ""))[:60],
                            "desc": str(r.get("desc", ""))[:200]})
        except Exception:
            pass
    vid = str(data.get("video", ""))[:200]
    m = re.search(r"(?:v=|youtu\.be/|embed/)([A-Za-z0-9_-]{11})", vid)
    if m:
        vid = m.group(1)
    c = {"id": "u_" + os.urandom(5).hex(),
         "title": str(data.get("title", ""))[:120] or "קמפיין ללא שם",
         "cat": str(data.get("cat", ""))[:40] or "כללי",
         "owner": str(data.get("owner", ""))[:80],
         "tagline": str(data.get("tagline", ""))[:200],
         "story": str(data.get("story", ""))[:4000],
         "image": imgpath, "video": vid,
         "goal": goal, "raised": 0, "backers": 0,
         "deadline": int(time.time()) + days * 86400,
         "contact": str(data.get("contact", ""))[:120], "rewards": rewards,
         "ts": int(time.time())}
    with CLOCK:
        items.append(c); items = items[-200:]; save_campaigns(items)
    return c
def pledge_campaign(cid, amount, name):
    try:
        amount = max(1, min(1000000, int(float(amount))))
    except Exception:
        return None
    with CLOCK:
        items = load_campaigns()
        if items is None:
            return None
        hit = None
        for c in items:
            if c.get("id") == cid:
                c["raised"] = int(c.get("raised", 0)) + amount
                c["backers"] = int(c.get("backers", 0)) + 1
                hit = c; break
        if not hit:
            return None
        save_campaigns(items)
    goal = max(1, int(hit.get("goal", 1)))
    return {"ok": True, "raised": hit["raised"], "backers": hit["backers"],
            "pct": min(100, round(hit["raised"] * 100 / goal))}

def save_image(dataurl):
    try:
        m = re.match(r"data:image/(png|jpe?g|gif|webp);base64,(.+)$", dataurl or "", re.I | re.S)
        if not m:
            return None
        ext = m.group(1).lower().replace("jpeg", "jpg")
        raw = base64.b64decode(m.group(2))
        if len(raw) > 4 * 1024 * 1024:   # 4MB cap
            return None
        updir = os.path.join(WEB, "uploads")
        os.makedirs(updir, exist_ok=True)
        fn = "c" + str(int(time.time())) + "_" + os.urandom(4).hex() + "." + ext
        with open(os.path.join(updir, fn), "wb") as f:
            f.write(raw)
        return "uploads/" + fn
    except Exception:
        return None

def add_comment(name, text, image=None, parent=None):
    name = (name or "").strip()[:40] or "אנונימי"
    text = (text or "").strip()[:1000]
    img = save_image(image) if image else None
    if not text and not img:
        return None
    item = {"id": os.urandom(6).hex(), "name": name, "text": text, "ts": int(time.time())}
    if img:
        item["img"] = img
    with CLOCK:
        items = load_comments()
        parent = (parent or "").strip()[:16]
        if parent and any(c.get("id") == parent for c in items):
            item["parent"] = parent
        items.append(item)
        items = items[-800:]
        save_comments(items)
    return item

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
    img = None; title = None; desc = None
    def meta(raw, key):
        for p in (r'<meta[^>]+property=["\']'+key+r'["\'][^>]+content=["\']([^"\']+)',
                  r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']'+key+r'["\']',
                  r'<meta[^>]+name=["\']'+key+r'["\'][^>]+content=["\']([^"\']+)'):
            m = re.search(p, raw, re.I)
            if m:
                return m.group(1).replace("&amp;", "&").strip()
        return None
    try:
        req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0 (compatible; AgroDataBot/1.0)"})
        raw = urllib.request.urlopen(req, timeout=10).read(500000).decode("utf-8", "ignore")
        im = meta(raw, "og:image") or meta(raw, "og:image:url") or meta(raw, "twitter:image")
        if im: img = urllib.parse.urljoin(u, im)
        title = meta(raw, "og:title") or meta(raw, "twitter:title")
        desc = meta(raw, "og:description") or meta(raw, "description") or meta(raw, "twitter:description")
        if not title:
            mt = re.search(r'<title[^>]*>([^<]+)</title>', raw, re.I)
            if mt: title = mt.group(1).strip()
    except Exception:
        pass
    out = {"url": u, "image": img, "title": title, "desc": desc}
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

def ask_gemini_media(q, media):
    """מולטימודאל — Gemini רואה תמונות/איורים/תרשימים/וידאו. q הוא ההנחיה המלאה (בלי עטיפת מערכת)."""
    if not GEMINI_KEY:
        return {"answer": "מנוע ה-AI אינו מחובר.", "demo": True}
    parts = [{"text": q}]
    for m in (media or [])[:6]:
        data = m.get("data", "")
        if not data:
            continue
        parts.append({"inline_data": {"mime_type": m.get("mime", "image/png"), "data": data}})
    url = "https://generativelanguage.googleapis.com/v1beta/models/" + GEMINI_MODEL + ":generateContent?key=" + GEMINI_KEY
    body = json.dumps({"contents": [{"parts": parts}],
                       "generationConfig": {"temperature": 0.4, "maxOutputTokens": 1024, "thinkingConfig": {"thinkingBudget": 0}}}).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=120))
        txt = d["candidates"][0]["content"]["parts"][0]["text"]
        return {"answer": txt.strip(), "demo": False}
    except Exception as e:
        return {"answer": "שגיאה בניתוח המדיה.", "demo": True, "err": getattr(e, "code", None)}

def extract_spreadsheet(b64, mime="", name=""):
    """מחלץ טקסט מקובץ CSV או XLSX (ספריות סטנדרט בלבד)."""
    import io, zipfile
    import xml.etree.ElementTree as ET
    try:
        raw = base64.b64decode(b64)
    except Exception:
        return ""
    lname = (name or "").lower()
    if lname.endswith(".csv") or (mime and "csv" in mime):
        try:
            return raw.decode("utf-8", "ignore")[:6000]
        except Exception:
            return raw.decode("latin-1", "ignore")[:6000]
    try:
        z = zipfile.ZipFile(io.BytesIO(raw))
        ns = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
        shared = []
        if "xl/sharedStrings.xml" in z.namelist():
            r = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in r.findall(ns + "si"):
                shared.append("".join(t.text or "" for t in si.iter(ns + "t")))
        out = []
        sheets = sorted(n for n in z.namelist() if n.startswith("xl/worksheets/sheet") and n.endswith(".xml"))
        for sh in sheets[:3]:
            r = ET.fromstring(z.read(sh))
            for row in r.iter(ns + "row"):
                cells = []
                for c in row.findall(ns + "c"):
                    t = c.get("t"); v = c.find(ns + "v"); val = ""
                    if v is not None and v.text is not None:
                        if t == "s":
                            try: val = shared[int(v.text)]
                            except Exception: val = v.text
                        else:
                            val = v.text
                    else:
                        istag = c.find(ns + "is")
                        if istag is not None:
                            val = "".join(tt.text or "" for tt in istag.iter(ns + "t"))
                    cells.append(val or "")
                if any(cells):
                    out.append("\t".join(cells))
        return "\n".join(out)[:6000]
    except Exception:
        return ""

NEWSCACHE = {}
def fetch_news(q, region):
    q = (q or 'agritech OR agtech OR "agriculture technology" OR "food tech"').strip()
    key = region + "|" + q
    now = time.time()
    if key in NEWSCACHE and now - NEWSCACHE[key][0] < 300:   # 5-min cache
        return NEWSCACHE[key][1]
    if region == "il":
        url = "https://news.google.com/rss/search?q=%s&hl=iw-IL&gl=IL&ceid=IL:iw"
    else:
        url = "https://news.google.com/rss/search?q=%s&hl=en-US&gl=US&ceid=US:en"
    url = url % urllib.parse.quote(q)
    out = []
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; AgroDataBot/1.0)"})
        raw = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        for it in re.findall(r"<item>(.*?)</item>", raw, re.S)[:100]:
            def g(tag):
                m = re.search(r"<" + tag + r"[^>]*>(.*?)</" + tag + r">", it, re.S)
                return (m.group(1).strip() if m else "")
            title = re.sub(r"^<!\[CDATA\[|\]\]>$", "", g("title"))
            link = g("link"); pub = g("pubDate")
            ms = re.search(r'<source[^>]*url="([^"]*)"[^>]*>(.*?)</source>', it, re.S)
            surl = ms.group(1) if ms else ""
            src = ms.group(2).strip() if ms else ""
            host = urllib.parse.urlparse(surl).netloc.lower()
            if region == "il":
                if not host.endswith(".il"):
                    continue   # Israel feed = Israeli sources only
            else:
                # World feed = real press only — drop PR / press-release wires & junk
                BADSRC = ("einpresswire", "globenewswire", "prnewswire", "businesswire", "accesswire",
                          "stocktitan", "benzinga", "marketscreener", "streetinsider", "prweb", "openpr",
                          "digitaljournal", "manilatimes", "finanznachrichten", "prlog", "issuewire", "newsfilecorp")
                if any(b in host for b in BADSRC):
                    continue
            if src and title.endswith(" - " + src):
                title = title[:-(len(src) + 3)]
            title = title.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
            if title and link:
                out.append({"title": title, "link": link, "source": src, "date": pub})
    except Exception:
        pass
    res = {"items": out}
    NEWSCACHE[key] = (now, res)
    return res

def fetch_research(q, frm):
    frm = re.sub(r"[^0-9\-]", "", frm or "")[:10] or "2021-01-01"
    base = ("https://api.openalex.org/works?filter=institutions.country_code:IL,"
            "concepts.id:C118518473,from_publication_date:" + frm +
            "&sort=publication_date:desc&per-page=30&mailto=krispelitzik@gmail.com")
    if q and q.strip():
        base += "&search=" + urllib.parse.quote(q.strip())
    try:
        req = urllib.request.Request(base, headers={"User-Agent": "AgroData/1.0 (mailto:krispelitzik@gmail.com)"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
        out = []
        for w in d.get("results", []):
            title = w.get("title") or ""
            if not title:
                continue
            authors = ", ".join((a.get("author", {}) or {}).get("display_name", "") for a in (w.get("authorships") or [])[:3])
            inst = ""
            for a in (w.get("authorships") or []):
                for it in (a.get("institutions") or []):
                    if it.get("country_code") == "IL":
                        inst = it.get("display_name", ""); break
                if inst:
                    break
            url = w.get("doi") or (w.get("primary_location", {}) or {}).get("landing_page_url") or w.get("id") or ""
            out.append({"title": title, "authors": authors, "year": w.get("publication_year"),
                        "inst": inst, "type": w.get("type", ""), "url": url})
        return {"items": out, "count": d.get("meta", {}).get("count")}
    except Exception as e:
        return {"items": [], "err": str(getattr(e, "code", "") or type(e).__name__)}

def fetch_weather(lat, lon):
    url = ("https://api.open-meteo.com/v1/forecast?latitude=" + str(lat) + "&longitude=" + str(lon) +
           "&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m,soil_temperature_0cm,soil_moisture_0_to_1cm&timezone=auto")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=15))
        return {"ok": True, "current": d.get("current", {}), "units": d.get("current_units", {})}
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__)}

# ---- AgroLake: central agricultural data repository (real open sources) ----
LAKECACHE = {}
WB = {  # World Bank indicators for Israel (ISR)
  "yield":  ("AG.YLD.CREL.KG",   "יבול דגנים",            "ק\"ג/הקטר",   "AG.YLD.CREL.KG"),
  "land":   ("AG.LND.AGRI.ZS",   "שטח חקלאי",             "% משטח הארץ", "AG.LND.AGRI.ZS"),
  "arable": ("AG.LND.ARBL.HA",   "אדמה בת-עיבוד",         "הקטר",        "AG.LND.ARBL.HA"),
  "water":  ("ER.H2O.FWAG.ZS",   "צריכת מים לחקלאות",     "% מכלל המים", "ER.H2O.FWAG.ZS"),
  "export": ("TX.VAL.FOOD.ZS.UN", "יצוא מזון",            "% מכלל היצוא", "TX.VAL.FOOD.ZS.UN"),
  "aqua":   ("ER.FSH.AQUA.MT",    "ייצור מדגה (חקלאות ימית)", "טון",     "ER.FSH.AQUA.MT"),
  "forest": ("AG.LND.FRST.ZS",    "שטח יער",               "% משטח הארץ", "AG.LND.FRST.ZS"),
  # SDG · food security & sustainability (World Bank, ISR)
  "foodprod":  ("AG.PRD.FOOD.XD",    "מדד ייצור מזון",        "אינדקס (2015=100)", "AG.PRD.FOOD.XD"),
  "cropprod":  ("AG.PRD.CROP.XD",    "מדד ייצור צומח",        "אינדקס (2015=100)", "AG.PRD.CROP.XD"),
  "lvskprod":  ("AG.PRD.LVSK.XD",    "מדד ייצור מהחי",        "אינדקס (2015=100)", "AG.PRD.LVSK.XD"),
  "undernour": ("SN.ITK.DEFC.ZS",    "תת-תזונה באוכלוסייה",   "% מהאוכלוסייה",      "SN.ITK.DEFC.ZS"),
  "foodinsec": ("SN.ITK.MSFI.ZS",    "חוסר-ביטחון תזונתי",    "% מהאוכלוסייה",      "SN.ITK.MSFI.ZS"),
  "foodimp":   ("TM.VAL.FOOD.ZS.UN", "יבוא מזון",             "% מכלל היבוא",       "TM.VAL.FOOD.ZS.UN"),
}
# World Bank indicators for other markets (country-specific)
WBC = {
  "br_yield": ("AG.YLD.CREL.KG", "BRA", "יבול דגנים · ברזיל",   "ק\"ג/הקטר"),
  "ar_yield": ("AG.YLD.CREL.KG", "ARG", "יבול דגנים · ארגנטינה", "ק\"ג/הקטר"),
  "ru_yield": ("AG.YLD.CREL.KG", "RUS", "יבול דגנים · רוסיה",    "ק\"ג/הקטר"),
  "cn_yield": ("AG.YLD.CREL.KG", "CHN", "יבול דגנים · סין",      "ק\"ג/הקטר"),
  "us_yield": ("AG.YLD.CREL.KG", "USA", "יבול דגנים · ארה\"ב",   "ק\"ג/הקטר"),
  "cn_land":  ("AG.LND.AGRI.ZS", "CHN", "שטח חקלאי · סין",       "% משטח"),
  "br_land":  ("AG.LND.AGRI.ZS", "BRA", "שטח חקלאי · ברזיל",     "% משטח"),
}
def _wb(ind, country="ISR"):
    url = ("https://api.worldbank.org/v2/country/" + country + "/indicator/" + ind +
           "?format=json&per_page=80")
    req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0"})
    d = json.load(urllib.request.urlopen(req, timeout=20))
    rows = [(r.get("date"), r.get("value")) for r in (d[1] or []) if r.get("value") is not None]
    rows.sort(key=lambda x: x[0])
    return rows[-24:]
def _climate():
    end = datetime.date.today()
    start = end - datetime.timedelta(days=730)
    url = ("https://archive-api.open-meteo.com/v1/archive?latitude=31.31&longitude=34.62"
           "&start_date=" + start.isoformat() + "&end_date=" + end.isoformat() +
           "&daily=temperature_2m_mean,precipitation_sum&timezone=auto")
    req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0"})
    d = json.load(urllib.request.urlopen(req, timeout=25))
    dl = d.get("daily", {})
    dates = dl.get("time", []); temps = dl.get("temperature_2m_mean", []); prec = dl.get("precipitation_sum", [])
    mon = {}
    for i, dt in enumerate(dates):
        m = dt[:7]
        mon.setdefault(m, [[], 0.0])
        if temps[i] is not None: mon[m][0].append(temps[i])
        if prec[i] is not None: mon[m][1] += prec[i]
    labels = sorted(mon.keys())
    tavg = [round(sum(mon[m][0]) / len(mon[m][0]), 1) if mon[m][0] else None for m in labels]
    psum = [round(mon[m][1], 1) for m in labels]
    return labels, [{"name": "טמפ' ממוצעת (°C)", "data": tavg},
                    {"name": "משקעים (מ\"מ)", "data": psum, "unit": "מ\"מ"}]
# Eurostat (EU open statistics, JSON-stat, no key)
EU = {
  "eu_cereal": ("apro_cpsh1", {"crops": "C0000", "strucpro": "HPRD_HUMD_EU_THS_T", "geo": "EU27_2020"},
                "ייצור דגנים · האיחוד האירופי", "אלף טון"),
  "eu_area":   ("apro_cpsh1", {"crops": "C0000", "strucpro": "AR_THS_HA", "geo": "EU27_2020"},
                "שטח דגנים · האיחוד האירופי", "אלף הקטר"),
  "eu_organic": ("sdg_02_40", {"geo": "EU27_2020"},
                "חקלאות אורגנית · האיחוד האירופי", "% מהשטח החקלאי"),
}
def fetch_eurostat(code, params):
    url = ("https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/" + code +
           "?format=JSON&" + urllib.parse.urlencode(params))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
    d = json.load(urllib.request.urlopen(req, timeout=25))
    ids = d["id"]; sizes = d["size"]
    strides = [1] * len(sizes)
    for i in range(len(sizes) - 2, -1, -1):
        strides[i] = strides[i + 1] * sizes[i + 1]
    tdim = ids.index("time")
    tcat = d["dimension"]["time"]["category"]["index"]
    years = sorted(tcat, key=lambda k: tcat[k])
    vals = d["value"]
    labels = []; series = []
    for y in years:
        pos = [0] * len(ids); pos[tdim] = tcat[y]
        idx = sum(pos[i] * strides[i] for i in range(len(ids)))
        v = vals.get(str(idx))
        if v is not None:
            labels.append(y); series.append(round(v, 2))
    return labels, series

def fetch_lake(ds):
    now = time.time()
    if ds in LAKECACHE and now - LAKECACHE[ds][0] < 3600:
        return LAKECACHE[ds][1]
    try:
        if ds == "climate":
            labels, series = _climate()
            out = {"ok": True, "id": ds, "title": "אקלים וקרקע · אופקים", "unit": "",
                   "source": "Open-Meteo (ERA5)", "source_url": "https://open-meteo.com/",
                   "note": "ממוצע חודשי · 24 חודשים אחרונים", "labels": labels, "series": series}
        elif ds in EU:
            code, params, title, unit = EU[ds]
            labels, vals = fetch_eurostat(code, params)
            out = {"ok": True, "id": ds, "title": title, "unit": unit,
                   "source": "Eurostat", "source_url": "https://ec.europa.eu/eurostat",
                   "note": "נתונים שנתיים · " + unit + " · EU27",
                   "labels": labels,
                   "series": [{"name": title + " (" + unit + ")", "data": vals, "unit": unit}]}
        elif ds in WBC:
            ind, cc, title, unit = WBC[ds]
            rows = _wb(ind, cc)
            out = {"ok": True, "id": ds, "title": title, "unit": unit,
                   "source": "World Bank Open Data", "source_url": "https://data.worldbank.org",
                   "note": "נתונים שנתיים · " + unit,
                   "labels": [r[0] for r in rows],
                   "series": [{"name": title + " (" + unit + ")",
                               "data": [round(r[1], 2) for r in rows], "unit": unit}]}
        elif ds in WB:
            ind, title, unit, _ = WB[ds]
            rows = _wb(ind)
            out = {"ok": True, "id": ds, "title": title + " · ישראל", "unit": unit,
                   "source": "World Bank Open Data", "source_url": "https://data.worldbank.org/country/israel",
                   "note": "נתונים שנתיים · " + unit,
                   "labels": [r[0] for r in rows],
                   "series": [{"name": title + " (" + unit + ")",
                               "data": [round(r[1], 2) for r in rows], "unit": unit}]}
        else:
            return {"ok": False, "err": "unknown dataset"}
        LAKECACHE[ds] = (now, out)
        return out
    except Exception as e:
        return {"ok": False, "id": ds, "err": str(getattr(e, "code", "") or type(e).__name__)}

# ---- data.gov.il — Israeli government open data (CKAN, no key) ----
GOVCACHE = {}
def fetch_govdata(q):
    q = (q or "חקלאות").strip()
    now = time.time()
    if q in GOVCACHE and now - GOVCACHE[q][0] < 900:   # 15-min cache
        return GOVCACHE[q][1]
    url = ("https://data.gov.il/api/3/action/package_search?rows=24&q=" +
           urllib.parse.quote(q))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
        res = d.get("result", {})
        out = []
        for x in res.get("results", []):
            org = (x.get("organization") or {}).get("title") or ""
            resfmts = sorted(set((r.get("format") or "").upper() for r in x.get("resources", []) if r.get("format")))
            out.append({
                "title": x.get("title") or x.get("name"),
                "org": org,
                "notes": (x.get("notes") or "").strip()[:220],
                "url": "https://data.gov.il/dataset/" + (x.get("name") or ""),
                "formats": resfmts,
                "resources": len(x.get("resources", [])),
                "updated": (x.get("metadata_modified") or "")[:10],
            })
        result = {"ok": True, "count": res.get("count", len(out)), "items": out}
        GOVCACHE[q] = (now, result)
        return result
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__), "items": []}

# ---- UN Comtrade — world trade flows (free preview, no key) ----
COMTRADE_PARTNERS = {}
TRADECACHE = {}
def _load_partners():
    if COMTRADE_PARTNERS:
        return COMTRADE_PARTNERS
    try:
        req = urllib.request.Request("https://comtradeapi.un.org/files/v1/app/reference/partnerAreas.json",
                                     headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        if isinstance(d, dict):
            d = d.get("results", [])
        for r in d:
            COMTRADE_PARTNERS[str(r.get("PartnerCode"))] = r.get("text") or r.get("PartnerDesc")
    except Exception:
        pass
    return COMTRADE_PARTNERS
def fetch_trade(cmd, flow, reporter="376", period="2023"):
    key = (cmd, flow, reporter, period)
    now = time.time()
    if key in TRADECACHE and now - TRADECACHE[key][0] < 3600:
        return TRADECACHE[key][1]
    url = ("https://comtradeapi.un.org/public/v1/preview/C/A/HS?reporterCode=" + reporter +
           "&period=" + period + "&cmdCode=" + cmd + "&flowCode=" + flow)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
        d = None
        for att in range(3):
            try:
                d = json.load(urllib.request.urlopen(req, timeout=25)); break
            except urllib.error.HTTPError as he:
                if he.code == 429 and att < 2:
                    time.sleep(2 + att * 2); continue
                raise
        names = _load_partners()
        rows = []
        for it in d.get("data", []):
            pc = str(it.get("partnerCode"))
            if pc == "0":            # skip World aggregate
                continue
            val = it.get("primaryValue")
            if not val:
                continue
            nm = names.get(pc, pc)
            if nm and ("nes" in nm or "not elsewhere" in nm.lower()):
                continue
            rows.append((nm, val))
        rows.sort(key=lambda x: x[1], reverse=True)
        rows = rows[:12]
        flowname = "יצוא" if flow == "X" else "יבוא"
        out = {"ok": True, "id": "trade", "title": flowname + " · " + period,
               "unit": "USD", "source": "UN Comtrade", "source_url": "https://comtrade.un.org",
               "note": "ערך סחר בדולרים · " + period + " · " + flowname + " (12 השותפים המובילים)",
               "labels": [r[0] for r in rows],
               "series": [{"name": "ערך סחר ($)", "data": [round(r[1]) for r in rows], "unit": "USD"}]}
        if not rows:
            out["ok"] = False; out["err"] = "no-data"
        TRADECACHE[key] = (now, out)
        return out
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__)}

# ---- AgroIndex: Israeli agri-tech ecosystem index, computed from our own data ----
AIDX_DEALS = [("IrriSense", 12, "השקיה ומים"), ("SkyAgro", 34, "רובוטיקה"), ("BeeHive Data", 8, "חישה ו-AI"),
              ("SoilX", 27, "חישה ו-AI"), ("FreshChain", 60, "פוד-טק"), ("AlgaeProtein", 15, "פוד-טק"),
              ("CropVision AI", 22, "חישה ו-AI"), ("VertiFarm", 18, "פוד-טק"), ("SeedGen", 48, "זרעים וגנטיקה"),
              ("AquaLoop", 9, "פוד-טק")]
AIDX_SECTORS = ["חישה ו-AI", "פוד-טק", "השקיה ומים", "רובוטיקה", "זרעים וגנטיקה", "ביו והגנת הצומח"]
AIDX_CAMPSEC = {"אנרגיה וסביבה": "ביו והגנת הצומח", "רחפנים ו-AI": "רובוטיקה", "פוד-טק": "פוד-טק",
                "רובוטיקה": "רובוטיקה", "השקיה ומים": "השקיה ומים", "חקלאות עירונית": "פוד-טק",
                "זרעים וגנטיקה": "זרעים וגנטיקה", "כללי": "ביו והגנת הצומח"}
def compute_agroindex():
    camps = load_campaigns() or []
    sec = {s: 0.0 for s in AIDX_SECTORS}
    deal_total = 0.0
    top = []
    for n, amt, s in AIDX_DEALS:
        v = amt * 1e6
        sec[s] += v; deal_total += v; top.append((n, s, v))
    camp_raised = 0; backers = 0
    for c in camps:
        r = int(c.get("raised", 0)); camp_raised += r; backers += int(c.get("backers", 0))
        cs = AIDX_CAMPSEC.get(c.get("cat"), "ביו והגנת הצומח")
        if cs in sec:
            sec[cs] += r
        top.append((c.get("title"), c.get("cat"), r))
    total = deal_total + camp_raised
    sectors = [{"name": s, "pct": (round(sec[s] / total * 100) if total else 0)} for s in AIDX_SECTORS]
    deals_count = len(AIDX_DEALS) + len(camps)
    idx = round(100 + deals_count * 2.2 + backers * 0.02 + camp_raised / 1e6 * 0.6 + deal_total / 1e6 * 0.12, 1)
    top.sort(key=lambda x: x[2], reverse=True)
    top = [{"name": t[0], "sector": t[1], "amount": t[2]} for t in top[:8]]
    return {"ok": True, "index": idx,
            "kpis": {"funding": total, "startups": 712, "deals": deals_count,
                     "backers": backers, "avg": (round(total / deals_count) if deals_count else 0)},
            "sectors": sectors, "top": top,
            "note": "מחושב חי מנתוני הזירה — AgroCapital + AgroInvest"}

# ---- data.gov.il datastore: Ministry of Agriculture pesticide registry (live rows) ----
PEST_RID = "cffe0c50-6856-4187-9315-51bc113cb718"   # מאגר חומרי הדברה · משרד החקלאות
PESTCACHE = {}
def fetch_pesticides(q, limit=25):
    q = (q or "").strip()
    key = (q, limit)
    now = time.time()
    if key in PESTCACHE and now - PESTCACHE[key][0] < 900:
        return PESTCACHE[key][1]
    url = ("https://data.gov.il/api/3/action/datastore_search?resource_id=" + PEST_RID +
           "&limit=" + str(limit) + ("&q=" + urllib.parse.quote(q) if q else ""))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        res = d.get("result", {})
        out = []
        for r in res.get("records", []):
            out.append({
                "name": r.get("שם תכשיר", ""), "name_en": r.get("שם תכשיר אנגלי", ""),
                "active": r.get("חומר פעיל", ""), "type": r.get("סוג פעילות", ""),
                "crop": r.get("גידול", ""), "pest": r.get("נגע", ""),
                "tox": r.get("רעילות", ""), "holder": r.get("בעל רשיון", ""),
                "dose": r.get("מינון ליישום", ""), "label": r.get("תווית", ""),
            })
        result = {"ok": True, "total": res.get("total", len(out)), "items": out}
        PESTCACHE[key] = (now, result)
        return result
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__), "items": []}

# ---- Medical cannabis registries (data.gov.il, live rows) ----
CANN = {
  "holders":    ("c05fc5e0-c292-4633-8b06-e4f8b635d2a0",
                 ["company_name", "type_description", "type", "notes"],
                 ["חברה / בעל רישיון", "סוג פעילות", "קטגוריה", "הערות"], "בעלי רישיון עיסוק בקנביס"),
  "pharmacies": ("f635f611-5b6d-4b21-9cd3-ce7b14da6c11",
                 ["pharmacy_name", "pharmacy_city", "pharmacy_street", "pharmacy_delivery"],
                 ["בית מרקחת", "עיר", "כתובת", "משלוח"], "בתי מרקחת מורשים לקנביס"),
  "doctors":    ("37f14c29-47af-4b6c-b38e-e08a15e15b5b",
                 ["dr_name", "specialty", "institution", "city"],
                 ["רופא/ה", "התמחות", "מוסד", "עיר"], "רופאים מוסמכים לרישיון קנביס"),
}
CANNCACHE = {}
def fetch_cannabis(ds, q, limit=40):
    if ds not in CANN:
        ds = "holders"
    rid, fields, labels, title = CANN[ds]
    key = (ds, q, limit)
    now = time.time()
    if key in CANNCACHE and now - CANNCACHE[key][0] < 900:
        return CANNCACHE[key][1]
    url = ("https://data.gov.il/api/3/action/datastore_search?resource_id=" + rid +
           "&limit=" + str(limit) + ("&q=" + urllib.parse.quote(q) if q else ""))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        res = d.get("result", {})
        rows = [[str(r.get(f, "") or "") for f in fields] for r in res.get("records", [])]
        out = {"ok": True, "title": title, "cols": labels, "total": res.get("total", len(rows)), "rows": rows}
        CANNCACHE[key] = (now, out)
        return out
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__), "rows": []}

# ---- AgroFlora: live plant identifier via iNaturalist (open, no key) ----
FLORACACHE = {}
def fetch_flora(q):
    q = (q or "").strip()
    if not q:
        return {"ok": True, "items": []}
    now = time.time()
    if q in FLORACACHE and now - FLORACACHE[q][0] < 900:
        return FLORACACHE[q][1]
    url = ("https://api.inaturalist.org/v1/taxa?iconic_taxa=Plantae&per_page=24&locale=he&q=" +
           urllib.parse.quote(q))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0 (krispelitzik@gmail.com)"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
        out = []
        for t in d.get("results", []):
            dp = t.get("default_photo") or {}
            out.append({
                "id": t.get("id"), "sci": t.get("name", ""),
                "he": t.get("preferred_common_name", ""),
                "rank": t.get("rank", ""), "obs": t.get("observations_count", 0),
                "photo": dp.get("medium_url") or dp.get("square_url") or "",
                "wiki": t.get("wikipedia_url") or "",
                "inat": "https://www.inaturalist.org/taxa/" + str(t.get("id", "")),
            })
        result = {"ok": True, "count": d.get("total_results", len(out)), "items": out}
        FLORACACHE[q] = (now, result)
        return result
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__), "items": []}

# ---- Israeli Companies Registrar (data.gov.il, live) — agri-tech company lookup ----
COMP_RID = "f004176c-b85f-4542-8901-7b3176f9a054"   # מאגר חברות · רשם החברות (728k)
COMPCACHE = {}
def fetch_companies(q, limit=30):
    q = (q or "חקלאות").strip()
    key = (q, limit)
    now = time.time()
    if key in COMPCACHE and now - COMPCACHE[key][0] < 900:
        return COMPCACHE[key][1]
    url = ("https://data.gov.il/api/3/action/datastore_search?resource_id=" + COMP_RID +
           "&limit=" + str(limit) + "&q=" + urllib.parse.quote(q))
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=25))
        res = d.get("result", {})
        out = []
        for c in res.get("records", []):
            out.append({
                "num": c.get("מספר חברה", ""), "name": c.get("שם חברה", ""),
                "name_en": c.get("שם באנגלית", ""), "type": c.get("סוג תאגיד", ""),
                "status": c.get("סטטוס חברה", ""), "purpose": (c.get("מטרת החברה") or "").strip(),
                "founded": (c.get("תאריך התאגדות") or "")[:10],
                "gov": c.get("חברה ממשלתית", ""),
            })
        result = {"ok": True, "total": res.get("total", len(out)), "items": out}
        COMPCACHE[key] = (now, result)
        return result
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__), "items": []}

APPSTORE_CACHE = {}
def fetch_appstore(term, country="us", limit=40):
    term = (term or "agriculture").strip()
    key = (term, country, limit)
    now = time.time()
    if key in APPSTORE_CACHE and now - APPSTORE_CACHE[key][0] < 3600:
        return APPSTORE_CACHE[key][1]
    url = ("https://itunes.apple.com/search?term=" + urllib.parse.quote(term) +
           "&entity=software&limit=" + str(limit) + "&country=" + country)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception as e:
        return {"ok": False, "items": [], "err": str(e)[:60]}
    items = []
    for a in d.get("results", []):
        items.append({
            "name": a.get("trackName"),
            "dev": a.get("artistName"),
            "rating": round(a.get("averageUserRating") or 0, 2),
            "reviews": a.get("userRatingCount") or 0,
            "genre": a.get("primaryGenreName"),
            "icon": a.get("artworkUrl100") or a.get("artworkUrl60"),
            "url": a.get("trackViewUrl"),
            "desc": (a.get("description") or "").replace("\n", " ")[:220],
            "price": a.get("formattedPrice") or "חינם",
        })
    out = {"ok": True, "count": d.get("resultCount", len(items)), "items": items}
    APPSTORE_CACHE[key] = (now, out)
    return out

BOOKS_CACHE = {}
GBOOKS_KEY = os.environ.get("GOOGLE_BOOKS_API_KEY", "")
def fetch_gbooks(q, num=30, lang="heb"):
    q = (q or "agriculture").strip()
    ck = ("gb", q, num, lang); now = time.time()
    if ck in BOOKS_CACHE and now - BOOKS_CACHE[ck][0] < 3600:
        return BOOKS_CACHE[ck][1]
    url = ("https://www.googleapis.com/books/v1/volumes?q=" + urllib.parse.quote(q) +
           "&langRestrict=" + lang + "&maxResults=" + str(min(40, num)) +
           "&orderBy=relevance&country=IL&key=" + GBOOKS_KEY)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception as e:
        return {"ok": False, "items": [], "err": str(e)[:80]}
    items = []
    for it in d.get("items", []):
        v = it.get("volumeInfo", {}) or {}
        a = it.get("accessInfo", {}) or {}
        img = (v.get("imageLinks") or {})
        cover = img.get("thumbnail") or img.get("smallThumbnail") or ""
        if cover.startswith("http://"):
            cover = "https://" + cover[7:]
        readable = a.get("viewability") in ("ALL_PAGES",) or (a.get("pdf", {}) or {}).get("isAvailable") or (a.get("epub", {}) or {}).get("isAvailable")
        items.append({
            "title": v.get("title", ""),
            "author": (v.get("authors") or [""])[0],
            "year": (v.get("publishedDate") or "")[:4],
            "editions": 0,
            "cover": cover,
            "scanned": bool(readable),
            "desc": (v.get("description") or (it.get("searchInfo", {}) or {}).get("textSnippet") or "")[:220],
            "subjects": [s for s in (v.get("categories") or [])[:3] if s],
            "read": a.get("webReaderLink") or v.get("infoLink") or v.get("previewLink") or "",
        })
    out = {"ok": True, "total": d.get("totalItems", len(items)), "items": items, "src": "gbooks"}
    BOOKS_CACHE[ck] = (now, out)
    return out

def fetch_books(q, num=30, lang=""):
    q = (q or "agriculture").strip()
    # עברית: Google Books נותן כיסוי עשיר בהרבה (אם יש מפתח)
    if lang == "heb" and GBOOKS_KEY:
        g = fetch_gbooks(q, num, "heb")
        if g.get("ok"):
            return g   # מחזיר גם אם ריק — לא ליפול ל-Open Library שיציג ספרים אנגליים
    if lang in ("heb", "eng"):
        q = q + " language:" + lang
    key = (q, num); now = time.time()
    if key in BOOKS_CACHE and now - BOOKS_CACHE[key][0] < 3600:
        return BOOKS_CACHE[key][1]
    url = ("https://openlibrary.org/search.json?q=" + urllib.parse.quote(q) +
           "&limit=" + str(num) + "&fields=title,author_name,first_publish_year,cover_i,ia,key,edition_count,first_sentence,subject")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception as e:
        return {"ok": False, "items": [], "err": str(e)[:60]}
    items = []
    for b in d.get("docs", []):
        ia = b.get("ia") or []
        cover = b.get("cover_i")
        items.append({
            "title": b.get("title", ""),
            "author": (b.get("author_name") or [""])[0],
            "year": b.get("first_publish_year") or "",
            "editions": b.get("edition_count") or 0,
            "cover": ("https://covers.openlibrary.org/b/id/" + str(cover) + "-M.jpg") if cover else "",
            "scanned": bool(ia),
            "desc": ((b.get("first_sentence") or [""])[0] or "")[:200],
            "subjects": [s for s in (b.get("subject") or [])[:3] if s],
            "read": ("https://archive.org/details/" + ia[0]) if ia else ("https://openlibrary.org" + (b.get("key") or "")),
        })
    out = {"ok": True, "total": d.get("numFound", len(items)), "items": items}
    BOOKS_CACHE[key] = (now, out)
    return out

PAT_CACHE = {}
def fetch_patents(q, num=30):
    q = (q or "agriculture").strip()
    key = (q, num); now = time.time()
    if key in PAT_CACHE and now - PAT_CACHE[key][0] < 3600:
        return PAT_CACHE[key][1]
    inner = "q=" + q + "&type=PATENT&num=" + str(num)
    url = "https://patents.google.com/xhr/query?url=" + urllib.parse.quote(inner) + "&exp="
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        d = json.load(urllib.request.urlopen(req, timeout=20))
    except Exception as e:
        return {"ok": False, "items": [], "err": str(e)[:60]}
    def strip(s): return re.sub(r"<[^>]+>", "", s or "").strip()
    cl = d.get("results", {}).get("cluster", [])
    res = cl[0].get("result", []) if cl else []
    items = []
    for r in res:
        p = r.get("patent", {})
        pn = p.get("publication_number", "")
        items.append({
            "num": pn, "title": strip(p.get("title", "")),
            "assignee": strip(p.get("assignee", "")), "inventor": strip(p.get("inventor", "")),
            "date": p.get("priority_date", "") or p.get("publication_date", "") or p.get("grant_date", ""),
            "country": pn[:2] if pn else "",
            "abstract": strip(p.get("snippet", ""))[:240],
            "url": ("https://patents.google.com/patent/" + pn) if pn else "https://patents.google.com/",
        })
    out = {"ok": True, "total": d.get("results", {}).get("total_num_results", len(items)), "items": items}
    PAT_CACHE[key] = (now, out)
    return out

GPLAY_CACHE = {}
def _gplay_app(aid):
    u = "https://play.google.com/store/apps/details?id=" + aid + "&hl=en&gl=us"
    try:
        d = urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0"}), timeout=15).read().decode("utf-8", "ignore")
    except Exception:
        return None
    t = re.search(r'<meta property="og:title" content="([^"]+)"', d)
    img = re.search(r'<meta property="og:image" content="([^"]+)"', d)
    desc = re.search(r'<meta property="og:description" content="([^"]+)"', d)
    star = re.search(r'"ratingValue":"?([0-9.]+)', d) or re.search(r'([0-9]\.[0-9])\s*star', d)
    revs = re.search(r'"ratingCount":"?([0-9]+)', d)
    name = ((t.group(1) if t else "") or "").replace(" - Apps on Google Play", "").strip()
    if not name:
        return None
    return {"name": name, "rating": round(float(star.group(1)), 2) if star else 0,
            "reviews": int(revs.group(1)) if revs else 0,
            "icon": img.group(1) if img else "", "desc": (desc.group(1) if desc else "").replace("\n", " ")[:200],
            "url": u.split("&hl=")[0], "dev": ""}
def fetch_googleplay(term, limit=15):
    term = (term or "agriculture").strip(); key = (term, limit); now = time.time()
    if key in GPLAY_CACHE and now - GPLAY_CACHE[key][0] < 3600:
        return GPLAY_CACHE[key][1]
    try:
        s = urllib.request.urlopen(urllib.request.Request(
            "https://play.google.com/store/search?q=" + urllib.parse.quote(term) + "&c=apps&hl=en&gl=us",
            headers={"User-Agent": "Mozilla/5.0"}), timeout=20).read().decode("utf-8", "ignore")
    except Exception as e:
        return {"ok": False, "items": [], "err": str(e)[:60]}
    ids = []
    for m in re.findall(r'/store/apps/details\?id=([a-zA-Z0-9._]+)', s):
        if m not in ids:
            ids.append(m)
    ids = ids[:limit]
    items = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
        for r in ex.map(_gplay_app, ids):
            if r:
                items.append(r)
    out = {"ok": True, "count": len(items), "items": items}
    GPLAY_CACHE[key] = (now, out)
    return out

COMP_KEYWORDS = ["חקלאות", "אגרו", "השקיה", "זרעים", "חממות", "דשן", "מדגה", "פוד טק"]
COMPSTATS = {}
def _comp_count(q):
    url = ("https://data.gov.il/api/3/action/datastore_search?resource_id=" + COMP_RID +
           "&limit=0" + ("&q=" + urllib.parse.quote(q) if q else ""))
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 AgroData/1.0"})
    return json.load(urllib.request.urlopen(req, timeout=20)).get("result", {}).get("total", 0)
def fetch_company_stats():
    now = time.time()
    if "s" in COMPSTATS and now - COMPSTATS["s"][0] < 21600:   # 6h cache
        return COMPSTATS["s"][1]
    try:
        stats = []
        counts = {}
        ths = []
        def work(kw): counts[kw] = _comp_count(kw)
        for kw in COMP_KEYWORDS + [""]:
            t = threading.Thread(target=work, args=(kw,)); t.start(); ths.append(t)
        for t in ths: t.join()
        for kw in COMP_KEYWORDS:
            stats.append({"term": kw, "count": counts.get(kw, 0)})
        out = {"ok": True, "total": counts.get("", 0), "stats": stats}
        COMPSTATS["s"] = (now, out)
        return out
    except Exception as e:
        return {"ok": False, "err": str(getattr(e, "code", "") or type(e).__name__), "stats": []}

def scan_sitemap():
    pages = []
    try:
        for f in sorted(os.listdir(WEB)):
            if f.endswith(".html"):
                title = f
                try:
                    raw = open(os.path.join(WEB, f), encoding="utf-8").read(8000)
                    m = re.search(r"<title[^>]*>([^<]+)</title>", raw, re.I)
                    if m:
                        title = re.sub(r"\s*·\s*AgroData.*$", "", m.group(1).strip()) or m.group(1).strip()
                except Exception:
                    pass
                pages.append({"file": f, "title": title})
    except Exception:
        pass
    apis = []
    try:
        src = open(os.path.join(HERE, "agro-proxy.py"), encoding="utf-8").read()
        apis = sorted(set(re.findall(r"/api/[a-z]+", src)))
    except Exception:
        pass
    return {"pages": pages, "apis": apis, "count": len(pages)}

def fetch_journal(issn):
    issn = re.sub(r"[^0-9Xx\-]", "", issn or "")[:9]
    if not issn:
        return {"items": []}
    url = ("https://api.crossref.org/journals/" + issn +
           "/works?rows=6&sort=published&order=desc"
           "&select=title,author,URL,DOI,published")
    req = urllib.request.Request(url, headers={"User-Agent": "AgroData/1.0 (mailto:krispelitzik@gmail.com)"})
    try:
        d = json.load(urllib.request.urlopen(req, timeout=20))
        out = []
        for it in d.get("message", {}).get("items", []):
            title = (it.get("title") or [""])[0]
            if not title:
                continue
            authors = ", ".join((a.get("family") or a.get("name") or "") for a in (it.get("author") or [])[:3])
            parts = ((it.get("published") or {}).get("date-parts") or [[None]])[0]
            year = parts[0] if parts else None
            link = it.get("URL") or (("https://doi.org/" + it["DOI"]) if it.get("DOI") else "")
            out.append({"title": title, "authors": authors, "year": year, "url": link})
        return {"items": out}
    except Exception as e:
        return {"items": [], "err": str(getattr(e, "code", "") or type(e).__name__)}

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
        if self.path.startswith("/api/research"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_research(qs.get("q", [""])[0], qs.get("from", ["2021-01-01"])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/weather"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            lat = qs.get("lat", ["31.31"])[0]; lon = qs.get("lon", ["34.62"])[0]
            out = fetch_weather(lat, lon)
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/agroindex"):
            body = json.dumps(compute_agroindex(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/campaigns"):
            body = json.dumps(list_campaigns(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/trade"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_trade(qs.get("cmd", ["1001"])[0], qs.get("flow", ["X"])[0],
                              qs.get("reporter", ["376"])[0], qs.get("period", ["2023"])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/cannabis"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_cannabis(qs.get("ds", ["holders"])[0], qs.get("q", [""])[0],
                                 min(60, int(qs.get("limit", ["40"])[0] or 40)))
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/flora"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_flora(qs.get("q", [""])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/company_stats"):
            out = fetch_company_stats()
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/companies"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_companies(qs.get("q", ["חקלאות"])[0], min(50, int(qs.get("limit", ["30"])[0] or 30)))
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/appstore"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_appstore(qs.get("q", ["agriculture"])[0], qs.get("country", ["us"])[0], min(60, int(qs.get("limit", ["40"])[0] or 40)))
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/books"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_books(qs.get("q", ["agriculture"])[0], min(48, int(qs.get("num", ["30"])[0] or 30)), qs.get("lang", [""])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/patents"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_patents(qs.get("q", ["agriculture"])[0], min(50, int(qs.get("num", ["30"])[0] or 30)))
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/googleplay"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_googleplay(qs.get("q", ["agriculture"])[0], min(24, int(qs.get("limit", ["15"])[0] or 15)))
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/pesticides"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_pesticides(qs.get("q", [""])[0], min(50, int(qs.get("limit", ["25"])[0] or 25)))
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/govdata"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_govdata(qs.get("q", ["חקלאות"])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/lake"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_lake(qs.get("ds", ["climate"])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/news"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_news(qs.get("q", [""])[0], qs.get("region", ["world"])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/sitemap"):
            body = json.dumps(scan_sitemap(), ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/journal"):
            qs = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            out = fetch_journal(qs.get("issn", [""])[0])
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/comments"):
            body = json.dumps({"comments": load_comments()[-200:]}, ensure_ascii=False).encode("utf-8")
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
    def do_POST(self):
        if self.path.startswith("/api/ask"):
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            except Exception:
                data = {}
            q = (data.get("q") or "").strip(); eng = data.get("engine", "gemini"); media = data.get("media") or []
            if not q:
                out = {"answer": "נא להזין שאלה.", "demo": True}
            elif media:
                out = ask_gemini_media(q, media)      # מולטימודאל תמיד דרך Gemini
            elif eng == "claude":
                out = ask_claude(q)
            else:
                out = ask_gemini(q)
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/xlsx"):
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            except Exception:
                data = {}
            text = extract_spreadsheet(data.get("data", ""), data.get("mime", ""), data.get("name", ""))
            body = json.dumps({"ok": bool(text), "text": text}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/apply"):
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            except Exception:
                data = {}
            rec = save_application(data)
            body = json.dumps({"ok": True, "id": rec.get("ts")}, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/campaign") or self.path.startswith("/api/pledge"):
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            except Exception:
                data = {}
            if self.path.startswith("/api/pledge"):
                out = pledge_campaign(data.get("id"), data.get("amount"), data.get("name")) or {"ok": False}
            else:
                c = create_campaign(data); out = {"ok": True, "id": c.get("id")}
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if out.get("ok") else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        if self.path.startswith("/api/comments"):
            try:
                n = int(self.headers.get("Content-Length", 0))
                data = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
            except Exception:
                data = {}
            item = add_comment(data.get("name"), data.get("text"), data.get("image"), data.get("parent"))
            out = {"ok": bool(item), "comment": item}
            body = json.dumps(out, ensure_ascii=False).encode("utf-8")
            self.send_response(200 if item else 400)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-store")
            self.end_headers(); self.wfile.write(body); return
        self.send_response(404); self.end_headers()

socketserver.ThreadingTCPServer.allow_reuse_address = True
with socketserver.ThreadingTCPServer((HOST, PORT), H) as httpd:
    print(f"AgroData live server → http://localhost:{PORT}/agro-stock.html")
    httpd.serve_forever()
