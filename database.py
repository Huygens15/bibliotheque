import sqlite3
import os
from werkzeug.security import generate_password_hash

DB_PATH = os.path.join(os.path.dirname(__file__),'data','bibliotheque.db')

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn =get_db()
    cursor = conn.cursor()
    
    # table de livres
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS livres (
            isbn     TEXT PRIMARY KEY,
            titre    TEXT NOT NULL,
            auteur   TEXT NOT NULL,
            categorie    TEXT NOT NULL,
            description     TEXT,
            disponible   INTEGER NOT NULL DEFAULT 1
        )
    """)
    
    # table des membres
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS membres (
            numero TEXT PRIMARY KEY,
            nom    TEXT NOT NULL,
            prenom TEXT NOT NULL,
            email  TEXT NOT NULL UNIQUE
        )
    ''')
    
    # table des emprunts
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS emprunts (
            id                 TEXT PRIMARY KEY,
            isbn_livre         TEXT NOT NULL,
            num_membre         TEXT NOT NULL,
            date_emprunt       TEXT NOT NULL,
            date_retour_prevue TEXT NOT NULL,
            date_retour_reelle TEXT,
            statut             TEXT NOT NULL DEFAULT 'en_cours',
            FOREIGN KEY (isbn_livre) REFERENCES livres(isbn),
            FOREIGN KEY (num_membre) REFERENCES membres(numero)
        )
    ''')
    
    # table utilisateurs
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS utilisateurs (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        email    TEXT NOT NULL UNIQUE,
        mot_de_passe TEXT NOT NULL,
        nom      TEXT NOT NULL,
        role     TEXT NOT NULL DEFAULT 'gerant'
        )
    ''')
    # Créer un compte admin par défaut si la table est vide
    admin = conn.execute('SELECT * FROM utilisateurs').fetchone()
    if not admin:
        conn.execute(
            'INSERT INTO utilisateurs VALUES (NULL, ?, ?, ?,?)',
            ('admin@bibliotheque.com', generate_password_hash('admin123'), 'Administrateur', 'admin')
        )
        print("Compte admin créé : admin@bibliotheque.com / admin123")
    
    conn.commit()
    conn.close()
    print("Base de données initialisée.")