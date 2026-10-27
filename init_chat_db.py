import sqlite3


DB_NAME = "database.db"

def create_chat_tables():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Conversations table
    cursor.execute("""
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

    # Chat Messages table
    cursor.execute("""
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

    conn.commit()
    conn.close()
    print("Chat tables created successfully!")

if __name__ == "__main__":
    create_chat_tables()