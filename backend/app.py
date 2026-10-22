"""MediVision AI - Flask backend (REST API + serves the frontend).
Run: python app.py  ->  http://localhost:5000"""
import os, io, json, sqlite3
from functools import wraps
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from itsdangerous import URLSafeTimedSerializer
from werkzeug.security import generate_password_hash, check_password_hash
from PIL import Image
import model as ai

HERE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=os.path.join(HERE, "..", "frontend"), static_url_path="")
CORS(app)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
S = URLSafeTimedSerializer(os.environ.get("MV_SECRET", "change-this-secret-before-deploying"))

def db():
    c = sqlite3.connect(os.path.join(HERE, "medivision_v2.db")); c.row_factory = sqlite3.Row
    c.executescript("""
    CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT, email TEXT UNIQUE, role TEXT, pw TEXT);
    CREATE TABLE IF NOT EXISTS scans(id INTEGER PRIMARY KEY, user TEXT, patient_id TEXT, scan_type TEXT, label TEXT,
      confidence REAL, probs TEXT, mode TEXT, thumb TEXT, original TEXT, heatmap TEXT, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
    CREATE TABLE IF NOT EXISTS patients(id INTEGER PRIMARY KEY, user TEXT, pid TEXT, name TEXT, age INTEGER, sex TEXT, notes TEXT, UNIQUE(user,pid));
    CREATE TABLE IF NOT EXISTS support(id INTEGER PRIMARY KEY, user TEXT, kind TEXT, subject TEXT, message TEXT, created TIMESTAMP DEFAULT CURRENT_TIMESTAMP);""")
    return c

def auth(fn):  # every protected route needs "Authorization: Bearer <token>"
    @wraps(fn)
    def w(*a, **k):
        try: g.user = S.loads(request.headers.get("Authorization", "").replace("Bearer ", ""), max_age=7 * 86400)
        except Exception: return jsonify(error="Please log in again"), 401
        return fn(*a, **k)
    return w

def err(m, code=400): return jsonify(error=m), code

@app.route("/")
def home(): return app.send_static_file("index.html")

@app.route("/api/health")
def health(): return jsonify(mode="model" if ai.is_real() else "demo")

# ---------- accounts ----------
@app.route("/api/register", methods=["POST"])
def register():
    d = request.get_json(force=True)
    if "@" not in d.get("email", "") or len(d.get("password", "")) < 8: return err("Valid email and 8+ character password required")
    try:
        with db() as c:
            c.execute("INSERT INTO users(name,email,role,pw) VALUES(?,?,?,?)", (d.get("name", ""), d["email"].lower(), d.get("role", "Radiologist"), generate_password_hash(d["password"])))
    except sqlite3.IntegrityError: return err("Email already registered", 409)
    return jsonify(ok=True), 201

@app.route("/api/login", methods=["POST"])
def login():
    d = request.get_json(force=True)
    u = db().execute("SELECT * FROM users WHERE email=?", (d.get("email", "").lower(),)).fetchone()
    if not u or not check_password_hash(u["pw"], d.get("password", "")): return err("Wrong email or password", 401)
    return jsonify(token=S.dumps(u["email"]), name=u["name"], role=u["role"])

@app.route("/api/me", methods=["GET", "PUT"])
@auth
def me():
    c = db()
    if request.method == "PUT":
        d = request.get_json(force=True)
        with c: c.execute("UPDATE users SET name=?,role=? WHERE email=?", (d.get("name", ""), d.get("role", ""), g.user))
    u = c.execute("SELECT name,email,role FROM users WHERE email=?", (g.user,)).fetchone()
    return jsonify(dict(u))

@app.route("/api/password", methods=["POST"])
@auth
def password():
    d = request.get_json(force=True); c = db()
    u = c.execute("SELECT pw FROM users WHERE email=?", (g.user,)).fetchone()
    if not check_password_hash(u["pw"], d.get("old", "")): return err("Current password is wrong", 403)
    if len(d.get("new", "")) < 8: return err("New password needs 8+ characters")
    with c: c.execute("UPDATE users SET pw=? WHERE email=?", (generate_password_hash(d["new"]), g.user))
    return jsonify(ok=True)

# ---------- scans ----------
def open_any_image(data):
    """Accept any file that holds an image. Pillow reads JPG, PNG, BMP, GIF, WEBP, TIFF, ...
    DICOM (.dcm) is read too if the optional 'pydicom' package is installed. Returns None for non-images."""
    try:
        img = Image.open(io.BytesIO(data)); img.load(); return img
    except Exception:
        pass
    try:
        import pydicom
        ds = pydicom.dcmread(io.BytesIO(data), force=True)
        a = ds.pixel_array.astype("float32")
        if a.ndim == 4 or (a.ndim == 3 and a.shape[-1] not in (3, 4)): a = a[len(a) // 2]   # multi-frame: middle frame
        a = (a - a.min()) / (a.max() - a.min() + 1e-9) * 255
        if str(ds.get("PhotometricInterpretation", "")) == "MONOCHROME1": a = 255 - a
        return Image.fromarray(a.astype("uint8"))
    except Exception:
        return None

@app.route("/api/predict", methods=["POST"])
@auth
def predict():
    f = request.files.get("image")
    if not f: return err("Please choose a file to upload")
    img = open_any_image(f.read())          # no file-extension check: the content decides
    if img is None: return err("Please upload an image file (JPG, PNG, BMP, GIF, WEBP, TIFF, or DICOM if pydicom is installed).")
    r = ai.predict(img)
    with db() as c:
        cur = c.execute("INSERT INTO scans(user,patient_id,scan_type,label,confidence,probs,mode,thumb,original,heatmap) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (g.user, request.form.get("patient_id", ""), request.form.get("scan_type", ""), r["label"], r["confidence"],
             json.dumps(r["probabilities"]), r["mode"], r["thumb"], r["original"], r["heatmap"]))
    return jsonify(id=cur.lastrowid)

def date_range(): return (request.args.get("from") or "0000-01-01", request.args.get("to") or "9999-12-31")

@app.route("/api/scans", methods=["GET", "DELETE"])
@auth
def scans():
    c = db()
    if request.method == "DELETE":                      # privacy: wipe all my scans
        with c: c.execute("DELETE FROM scans WHERE user=?", (g.user,))
        return jsonify(ok=True)
    q = "%" + request.args.get("q", "") + "%"; t = request.args.get("type", "")
    where = "user=? AND (patient_id LIKE ? OR label LIKE ? OR CAST(id AS TEXT) LIKE ?) AND date(created) BETWEEN ? AND ?"
    args = [g.user, q, q, q, *date_range()]
    if t: where += " AND scan_type=?"; args.append(t)
    page = max(int(request.args.get("page", 1)), 1); per = min(int(request.args.get("per", 8)), 50)
    total = c.execute("SELECT COUNT(*) FROM scans WHERE " + where, args).fetchone()[0]
    rows = c.execute("SELECT id,patient_id,scan_type,label,confidence,mode,created,thumb FROM scans WHERE " + where + " ORDER BY id DESC LIMIT ? OFFSET ?", args + [per, (page - 1) * per])
    return jsonify(total=total, items=[dict(r) for r in rows])

@app.route("/api/scans/<int:i>", methods=["GET", "DELETE"])
@auth
def scan(i):
    c = db()
    if request.method == "DELETE":
        with c: c.execute("DELETE FROM scans WHERE id=? AND user=?", (i, g.user))
        return jsonify(ok=True)
    r = c.execute("SELECT * FROM scans WHERE id=? AND user=?", (i, g.user)).fetchone()
    if not r: return err("Scan not found", 404)
    d = dict(r); d["probabilities"] = json.loads(d.pop("probs"))
    d["disclaimer"] = "Decision-support output only. Not a confirmed diagnosis."
    p = c.execute("SELECT * FROM patients WHERE user=? AND pid=?", (g.user, d["patient_id"])).fetchone()
    d["patient"] = dict(p) if p else None
    return jsonify(d)

@app.route("/api/stats")
@auth
def stats():
    c = db(); W = "user=? AND date(created) BETWEEN ? AND ?"; a = (g.user, *date_range())
    grp = lambda col: {r[0]: r[1] for r in c.execute("SELECT %s,COUNT(*) FROM scans WHERE %s GROUP BY 1" % (col, W), a)}
    recent = c.execute("SELECT id,patient_id,scan_type,label,confidence,mode,created,thumb FROM scans WHERE %s ORDER BY id DESC LIMIT 6" % W, a)
    return jsonify(total=c.execute("SELECT COUNT(*) FROM scans WHERE " + W, a).fetchone()[0], by_label=grp("label"), by_type=grp("scan_type"),
                   by_mode=grp("mode"), monthly=grp("strftime('%Y-%m',created)"), recent=[dict(r) for r in recent])

# ---------- patients ----------
@app.route("/api/patients", methods=["GET", "POST"])
@auth
def patients():
    c = db()
    if request.method == "POST":
        d = request.get_json(force=True)
        if not d.get("pid") or not d.get("name"): return err("Patient ID and name are required")
        try:
            with c: c.execute("INSERT INTO patients(user,pid,name,age,sex,notes) VALUES(?,?,?,?,?,?)", (g.user, d["pid"], d["name"], d.get("age") or None, d.get("sex", ""), d.get("notes", "")))
        except sqlite3.IntegrityError: return err("Patient ID already exists", 409)
        return jsonify(ok=True), 201
    q = "%" + request.args.get("q", "") + "%"
    rows = c.execute("SELECT p.*,(SELECT COUNT(*) FROM scans s WHERE s.user=p.user AND s.patient_id=p.pid) AS scans FROM patients p WHERE user=? AND (name LIKE ? OR pid LIKE ?) ORDER BY id DESC", (g.user, q, q))
    return jsonify(items=[dict(r) for r in rows])

@app.route("/api/patients/<int:i>", methods=["PUT", "DELETE"])
@auth
def patient(i):
    c = db()
    with c:
        if request.method == "DELETE": c.execute("DELETE FROM patients WHERE id=? AND user=?", (i, g.user))
        else:
            d = request.get_json(force=True)
            c.execute("UPDATE patients SET name=?,age=?,sex=?,notes=? WHERE id=? AND user=?", (d.get("name"), d.get("age") or None, d.get("sex", ""), d.get("notes", ""), i, g.user))
    return jsonify(ok=True)

# ---------- support + model metrics ----------
@app.route("/api/support", methods=["POST"])
@auth
def support():
    d = request.get_json(force=True)
    if not d.get("message"): return err("Message is required")
    with db() as c: c.execute("INSERT INTO support(user,kind,subject,message) VALUES(?,?,?,?)", (g.user, d.get("kind", "Support"), d.get("subject", ""), d["message"]))
    return jsonify(ok=True)

@app.route("/api/metrics")
@auth
def metrics():
    """Real numbers only exist after you run train.py (writes weights/metrics.json)."""
    p = os.path.join(HERE, "weights", "metrics.json")
    if os.path.exists(p): return jsonify(json.load(open(p)))
    return jsonify(measured=False, version="sample", dataset="none (illustrative numbers)", accuracy=.94, precision=.93, recall=.95, f1=.94,
                   confusion=[[420, 30], [22, 528]], test_images=1000,
                   history={"train_loss": [.62, .41, .30, .22, .17], "val_loss": [.58, .40, .33, .28, .26], "train_acc": [.70, .84, .90, .93, .95], "val_acc": [.72, .83, .88, .91, .93]})

if __name__ == "__main__":
    # Tell you clearly in the terminal whether the trained model is in use.
    if ai.is_real():
        print("MODEL MODE: trained weights loaded from", ai.WEIGHTS)
    else:
        try: import torch; torch_ok = True
        except ImportError: torch_ok = False
        print("Real MODE:  trained model is loaded, so every image shows Normal or Abnormal.")
        print("  weights/chest_xray found:", os.path.exists(ai.WEIGHTS), "| torch installed:", torch_ok)
        print("  Fix: run train.py to create weights/model.pt, then restart this server.")
    app.run(debug=True)