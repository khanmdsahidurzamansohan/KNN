import os
import sqlite3
from functools import wraps

from flask import (
    Flask, render_template, request, jsonify,
    redirect, url_for, session, flash
)
from flask_socketio import SocketIO, emit, join_room
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# Load settings from .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv(
    "FLASK_SECRET_KEY",
    "change-this-secret-key-before-deployment"
)

def current_user_language(user_id):
    return session.get("user_language", "en")

SUPPORTED_LANGUAGES = {
    "bn": "Bangla",
    "en": "English",
    "ko": "Korean"
}
socketio = SocketIO(app, cors_allowed_origins="*")
DB_PATH = os.path.join(os.path.dirname(__file__), "knn.db")


# ---------------- DATABASE ----------------

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with db() as con:
        con.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        """)
        
        con.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user1_id INTEGER NOT NULL,
            user2_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user1_id) REFERENCES users (id),
            FOREIGN KEY (user2_id) REFERENCES users (id),
            UNIQUE(user1_id, user2_id)
        );
        """)

        con.execute("""
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            conversation_id INTEGER NOT NULL,
            sender_id INTEGER NOT NULL,
            original_text TEXT NOT NULL,
            source_language TEXT NOT NULL,
            translated_text TEXT,
            target_language TEXT NOT NULL,
            translation_status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (conversation_id) REFERENCES conversations (id),
            FOREIGN KEY (sender_id) REFERENCES users (id)
        );
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                feature TEXT NOT NULL,
                source_text TEXT NOT NULL,
                result_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)

        con.execute("""
            CREATE TABLE IF NOT EXISTS favorites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                source_text TEXT NOT NULL,
                result_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        """)


init_db()


# ---------------- LOGIN PROTECTION ----------------

def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({
                    "error": "Please log in first."
                }), 401

            return redirect(url_for("login"))

        return fn(*args, **kwargs)

    return wrapper


@app.context_processor
def inject_user():
    return {
        "current_user": session.get("user_name")
    }


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------- LOGIN PAGE ----------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with db() as con:
            user = con.execute(
                "SELECT * FROM users WHERE email = ?",
                (email,)
            ).fetchone()

        if user and check_password_hash(
            user["password_hash"], password
        ):
            session.update({
                "user_id": user["id"],
                "user_name": user["name"],
                "user_email": user["email"]
            })

            return redirect(url_for("dashboard"))

        flash("Email or password is incorrect.", "error")

    return render_template("login.html")


# ---------------- REGISTER PAGE ----------------

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash(
                "Enter your name and email. "
                "Password must be at least 8 characters.",
                "error"
            )
            return render_template("register.html")

        try:
            with db() as con:
                con.execute(
                    """
                    INSERT INTO users (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (
                        name,
                        email,
                        generate_password_hash(password)
                    )
                )

            flash("Account created. Please log in.", "success")
            return redirect(url_for("login"))

        except sqlite3.IntegrityError:
            flash("That email already has an account.", "error")

    return render_template("register.html")


# ---------------- LOGOUT ----------------

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------- DASHBOARD ----------------

@app.route("/dashboard")
@login_required
def dashboard():
    with db() as con:
        count = con.execute(
            "SELECT COUNT(*) FROM history WHERE user_id = ?",
            (session["user_id"],)
        ).fetchone()[0]

        fav_count = con.execute(
            "SELECT COUNT(*) FROM favorites WHERE user_id = ?",
            (session["user_id"],)
        ).fetchone()[0]

        recent = con.execute(
            """
            SELECT * FROM history
            WHERE user_id = ?
            ORDER BY id DESC LIMIT 4
            """,
            (session["user_id"],)
        ).fetchall()

    return render_template(
        "dashboard.html",
        count=count,
        fav_count=fav_count,
        recent=recent
    )


# ---------------- FEATURE PAGES ----------------

@app.route("/translate")
def translate_page():
    return render_template("translate.html")


@app.route("/understand")
def understand_page():
    return render_template("understand.html")


@app.route("/reply")
def reply_page():
    return render_template("reply.html")


@app.route("/situations")
def situations_page():
    return render_template("situations.html")


@app.route("/learning")
def learning_page():
    return render_template("learning.html")


# ---------------- HISTORY PAGE ----------------

@app.route("/history")
@login_required
def history_page():
    with db() as con:
        rows = con.execute(
            """
            SELECT * FROM history
            WHERE user_id = ?
            ORDER BY id DESC LIMIT 100
            """,
            (session["user_id"],)
        ).fetchall()

    return render_template("history.html", rows=rows)


# ---------------- FAVORITES PAGE ----------------

@app.route("/favorites")
@login_required
def favorites_page():
    with db() as con:
        rows = con.execute(
            """
            SELECT * FROM favorites
            WHERE user_id = ?
            ORDER BY id DESC
            """,
            (session["user_id"],)
        ).fetchall()

    return render_template("favorites.html", rows=rows)


# ---------------- GEMINI AI ----------------

def ask_gemini(prompt):
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        return None, (
            "Add GEMINI_API_KEY to your .env file "
            "to enable AI responses."
        )

    try:
        from google import genai

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=os.getenv(
                "GEMINI_MODEL",
                "gemini-3.8-flash"
            ),
            contents=prompt
        )

        return response.text, None

    except Exception as exc:
        print("Gemini error:", exc)
        return None, (
            "AI request failed. Check your API key, "
            "internet connection, model access, and quota."
        )


def translate_chat_message(text, source_lang, target_lang):
    source_name = SUPPORTED_LANGUAGES.get(source_lang, source_lang)
    target_name = SUPPORTED_LANGUAGES.get(target_lang, target_lang)

    if source_lang == target_lang:
        return text, None

    prompt = f"""
Translate the following chat message precisely from {source_name} to {target_name}. 
Provide ONLY the translated text without extra formatting, explanations, or quotes.

Message: {text}
"""
    translated, error = ask_gemini(prompt)
    if error:
        return text, error
    return translated.strip(), None


# ---------------- AI ASSISTANT API ----------------

@app.route("/api/assistant", methods=["POST"])
def assistant_api():
    data = request.get_json(silent=True) or {}

    feature = str(data.get("feature", "translate"))
    text = str(data.get("text", "")).strip()
    source = str(data.get("source", "Korean"))
    target = str(data.get("target", "English"))
    situation = str(data.get("situation", "Daily life"))

    if not text:
        return jsonify({
            "error": "Please enter some text first."
        }), 400

    if len(text) > 5000:
        return jsonify({
            "error": "Please keep input under 5,000 characters."
        }), 400

    if feature == "translate":
        prompt = f"""
You are KNN (Korean Native Navigator), a careful
Korean communication assistant.

Translate the user's text from {source} to {target}.
Situation: {situation}.

Return clear, useful output with these exact headings:
Translation:
Alternative:
Meaning and context:
Tone and formality:
Important vocabulary:

Keep the translation natural and do not invent details.

User text:
{text}
"""

    elif feature == "understand":
        prompt = f"""
You are KNN, an assistant for international
students in Korea.

Explain this Korean text for a learner.
Include English meaning, Bangla meaning, simple
explanation, context, tone/formality, and important
vocabulary.

Be accurate and concise.

Text:
{text}
"""

    elif feature == "reply":
        prompt = f"""
You are KNN, a Korean communication coach.

Situation: {situation}

Message received:
{text}

Suggest one natural and appropriate Korean reply.
Then provide its English meaning, Bangla meaning,
and a short explanation of politeness and tone.

Do not assume facts not supplied.
"""

    elif feature == "learning":
        prompt = f"""
You are KNN, a Korean language tutor for
international students.

Teach the topic:
{text}

Give 5 practical Korean expressions with Hangul,
pronunciation guide, English meaning, Bangla meaning,
and a short example situation.
"""

    else:
        return jsonify({
            "error": "Unknown feature."
        }), 400

    answer, error = ask_gemini(prompt)

    if error:
        return jsonify({"error": error}), 503

    if session.get("user_id"):
        with db() as con:
            con.execute(
                """
                INSERT INTO history
                (user_id, feature, source_text, result_text)
                VALUES (?, ?, ?, ?)
                """,
                (
                    session["user_id"],
                    feature,
                    text,
                    answer
                )
            )

    return jsonify({"result": answer})


# ---------------- SAVE FAVORITE ----------------

@app.route("/api/favorite", methods=["POST"])
@login_required
def favorite_api():
    data = request.get_json(silent=True) or {}

    source = str(data.get("source", "")).strip()
    result = str(data.get("result", "")).strip()

    if not source or not result:
        return jsonify({
            "error": "Nothing to save yet."
        }), 400

    with db() as con:
        con.execute(
            """
            INSERT INTO favorites (user_id, source_text, result_text)
            VALUES (?, ?, ?)
            """,
            (
                session["user_id"],
                source,
                result
            )
        )

    return jsonify({
        "message": "Saved to favorites."
    })


# ---------------- CHAT & SOCKET ROUTES ----------------

@app.route("/chat")
@login_required
def chat_page():
    uid = session["user_id"]
    with db() as con:
        chats = con.execute("""SELECT c.id AS conversation_id,
            CASE WHEN c.user1_id=? THEN u2.id ELSE u1.id END AS other_user_id,
            CASE WHEN c.user1_id=? THEN u2.name ELSE u1.name END AS other_name,
            CASE WHEN c.user1_id=? THEN u2.email ELSE u1.email END AS other_email
            FROM conversations c JOIN users u1 ON u1.id=c.user1_id
            JOIN users u2 ON u2.id=c.user2_id
            WHERE c.user1_id=? OR c.user2_id=? ORDER BY c.id DESC""",
            (uid, uid, uid, uid, uid)).fetchall()
    return render_template("chat.html", chats=chats, languages=SUPPORTED_LANGUAGES,
                           selected_language=current_user_language(uid),
                           current_user_id=uid)


@app.route("/api/chat/start", methods=["POST"])
@login_required
def start_chat():
    data = request.get_json(silent=True) or {}
    email = str(data.get("email", "")).strip().lower()
    if not email:
        return jsonify({"error": "Enter your friend's registered email."}), 400
    uid = session["user_id"]
    with db() as con:
        friend = con.execute("SELECT id,name FROM users WHERE email=?", (email,)).fetchone()
        if not friend:
            return jsonify({"error": "No KNN account found for that email. Ask your friend to register first."}), 404
        if friend["id"] == uid:
            return jsonify({"error": "You cannot chat with yourself."}), 400
        u1, u2 = sorted((uid, friend["id"]))
        con.execute("INSERT OR IGNORE INTO conversations (user1_id,user2_id) VALUES (?,?)", (u1, u2))
        conv = con.execute("SELECT id FROM conversations WHERE user1_id=? AND user2_id=?", (u1, u2)).fetchone()
    return jsonify({"conversation_id": conv["id"], "friend_name": friend["name"],
                    "redirect": url_for("chat_page", conversation=conv["id"])})


def can_access_conversation(uid, cid):
    with db() as con:
        return con.execute("SELECT id FROM conversations WHERE id=? AND (user1_id=? OR user2_id=?)",
                           (cid, uid, uid)).fetchone() is not None


@app.route("/api/chat/<int:cid>/messages")
@login_required
def chat_messages(cid):
    uid = session["user_id"]
    if not can_access_conversation(uid, cid):
        return jsonify({"error": "Conversation not found."}), 404
    with db() as con:
        rows = con.execute("""SELECT m.id,m.sender_id,u.name AS sender_name,m.original_text,
            m.source_language,m.translated_text,m.target_language,m.translation_status,m.created_at
            FROM chat_messages m JOIN users u ON u.id=m.sender_id
            WHERE m.conversation_id=? ORDER BY m.id ASC LIMIT 300""", (cid,)).fetchall()
    return jsonify({"messages": [dict(r) for r in rows]})


@socketio.on("join_chat")
def socket_join_chat(data):
    uid = session.get("user_id")
    if not uid:
        emit("chat_error", {"error": "Please log in first."})
        return
    try:
        cid = int((data or {}).get("conversation_id", 0))
    except (TypeError, ValueError):
        emit("chat_error", {"error": "Invalid conversation."})
        return
    if not can_access_conversation(uid, cid):
        emit("chat_error", {"error": "You do not have access to this conversation."})
        return
    join_room(f"conversation_{cid}")
    emit("joined_chat", {"conversation_id": cid})


@socketio.on("send_chat_message")
def socket_send_chat_message(data):
    uid = session.get("user_id")
    if not uid:
        emit("chat_error", {"error": "Please log in first."})
        return
    data = data or {}
    try:
        cid = int(data.get("conversation_id", 0))
    except (TypeError, ValueError):
        emit("chat_error", {"error": "Invalid conversation."})
        return
    text = str(data.get("text", "")).strip()
    source_code = str(data.get("source_language", current_user_language(uid)))
    if not text:
        emit("chat_error", {"error": "Type a message first."})
        return
    if len(text) > 2000:
        emit("chat_error", {"error": "Messages must be 2,000 characters or fewer."})
        return
    if source_code not in SUPPORTED_LANGUAGES:
        emit("chat_error", {"error": "Choose Bangla, English, or Korean."})
        return
    if not can_access_conversation(uid, cid):
        emit("chat_error", {"error": "You do not have access to this conversation."})
        return
    with db() as con:
        conv = con.execute("SELECT * FROM conversations WHERE id=?", (cid,)).fetchone()
        recipient_id = conv["user2_id"] if conv["user1_id"] == uid else conv["user1_id"]
        target_code = current_user_language(recipient_id)
        
    translated, err = translate_chat_message(text, source_code, target_code)
    status = "completed" if not err else "failed"
    
    with db() as con:
        cur = con.execute("""INSERT INTO chat_messages
            (conversation_id,sender_id,original_text,source_language,translated_text,target_language,translation_status)
            VALUES (?,?,?,?,?,?,?)""", (cid, uid, text, source_code, translated, target_code, status))
        row = con.execute("""SELECT m.id,m.sender_id,u.name AS sender_name,m.original_text,
            m.source_language,m.translated_text,m.target_language,m.translation_status,m.created_at
            FROM chat_messages m JOIN users u ON u.id=m.sender_id WHERE m.id=?""",
            (cur.lastrowid,)).fetchone()
            
    payload = dict(row)
    payload["conversation_id"] = cid

    if 'err' in locals() and err:
        payload["translation_error"] = err

    emit("new_chat_message", payload, to=f"conversation_{cid}")


@app.route("/language_settings", methods=["GET", "POST"])
def language_settings():
    if request.method == "POST":
        selected_lang = request.form.get("language")
        if selected_lang:
            session["user_language"] = selected_lang
            return redirect(url_for("chat_page"))

    return render_template("language_settings.html", languages=SUPPORTED_LANGUAGES)


if __name__ == "__main__":
    socketio.run(app, host=os.getenv("HOST", "127.0.0.1"),
                 port=int(os.getenv("PORT", "5000")),
                 debug=os.getenv("FLASK_DEBUG", "1") == "1")