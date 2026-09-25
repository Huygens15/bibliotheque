from flask import Flask, render_template, request, flash, redirect, url_for, session
from database import init_db, get_db
from functools import wraps
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3

# protection des pages 
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'utilisateur_id' not in session:
            flash('Veuillez vous connecter pour accéder à cette page.', 'error')
            return redirect(url_for('connexion'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorarted_function(*args, **kwargs):
        if session.get('utilisateur_role') != 'admin':
            flash("Accès réservé à l'administrateur.",'erreur' )
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorarted_function
            
            
app = Flask(__name__)

# clé secrète 
app.secret_key = 'bibliotheque_secret_2024'

# permet d'appeler la fonction inti_db à chaque fois 
# @app.before_request
# def setup():
#     init_db()
# Initialisation de la base au démarrage de l'app
with app.app_context():
    init_db()

@app.route('/')
@login_required
def index():
    db = get_db()

    nb_livres      = db.execute('SELECT COUNT(*) FROM livres').fetchone()[0]
    nb_disponibles = db.execute('SELECT COUNT(*) FROM livres WHERE disponible=1').fetchone()[0]
    nb_membres     = db.execute('SELECT COUNT(*) FROM membres').fetchone()[0]
    nb_emprunts    = db.execute("SELECT COUNT(*) FROM emprunts WHERE statut='en_cours'").fetchone()[0]

    aujourd_hui = datetime.now().strftime('%Y-%m-%d')
    nb_retards  = db.execute(
        "SELECT COUNT(*) FROM emprunts WHERE statut='en_cours' AND date_retour_prevue < ?",
        (aujourd_hui,)
    ).fetchone()[0]
    
    derniers_emprunts = db.execute('''
        SELECT e.id, l.titre, m.prenom || ' ' || m.nom AS membre_nom,
               e.date_emprunt, e.date_retour_prevue, e.statut
        FROM emprunts e
        JOIN livres l ON e.isbn_livre = l.isbn
        JOIN membres m ON e.num_membre = m.numero
        ORDER BY e.date_emprunt DESC
        LIMIT 5
    ''').fetchall()
    
    db.close()
    return render_template('index.html',
                           nb_disponibles=nb_disponibles,
                           nb_livres=nb_livres,
                           nb_emprunts=nb_emprunts,
                           nb_membres=nb_membres,
                           derniers_emprunts=derniers_emprunts,
                           aujourd_hui=aujourd_hui,
                           nb_retards=nb_retards)

# route pour les livres
@app.route('/livres')
@login_required
def livres():
    db = get_db()
    
    recherche = request.args.get('q','').strip()
    
    if recherche:
        liste = db.execute('''
                           SELECT * FROM livres
                           WHERE titre LIKE ? OR auteur LIKE ? OR isbn LIKE ? OR categorie LIKE ?
                           ORDER BY titre
                           ''', [f'%{recherche}%']*4).fetchall()
    else:
        liste = db.execute('SELECT * FROM livres ORDER BY titre').fetchall()
    db.close()
    return render_template('livres.html', livres = liste, recherche=recherche)

# route pour ajouter un livre
@app.route('/livres/ajouter', methods=['POST'])
def ajouter_livre():
    isbn =request.form['isbn'].strip()
    titre =request.form['titre'].strip()
    auteur =request.form['auteur'].strip()
    categorie =request.form['categorie'].strip()
    description = request.form.get('description', '').strip()

    if not all([isbn, titre, auteur, categorie]):
        flash('Tous les champs sont obligatoires.', 'erreur')
        return redirect(url_for('livres'))

    db = get_db()
    try:
        db.execute(
            'INSERT INTO livres VALUES (?, ?, ?, ?,?, 1)',
            (isbn, titre, auteur, categorie,description)
        )
        db.commit()
        flash(f'Livre « {titre} » ajouté avec succès !', 'succès')
    except Exception:
        flash(f"Un livre avec l'ISBN {isbn} existe déjà.", 'erreur')
    finally:
        db.close()
    
    return redirect(url_for('livres'))

# suppression d'un livre
@app.route('/livres/supprimer/<isbn>', methods=['POST'])
def supprimer_livre(isbn):
    db = get_db()
    livre = db.execute('SELECT * FROM livres WHERE isbn=?', (isbn,)).fetchone()
    if not livre:
        flash('Livre introuvable.', 'error')
    elif not livre['disponible']:
        flash(f'Impossible : « {livre["titre"]} » est actuellement emprunté.', 'erreur')
    else:
        db.execute('DELETE FROM livres WHERE isbn=?', (isbn,))
        db.commit()
        flash(f'Livre « {livre["titre"]} » supprimé.', 'succès')
    db.close()
    return redirect(url_for('livres'))
    
# route pour les membres
@app.route('/membres')
@login_required
def membres():
    db = get_db()
    recherche = request.args.get('q', '').strip()
    
    if recherche:
        liste = db.execute('''
            SELECT * FROM membres
            WHERE nom LIKE ? OR prenom LIKE ? OR email LIKE ? OR numero LIKE ?
            ORDER BY nom
        ''', [f'%{recherche}%'] * 4).fetchall()
    
    else:
        liste = db.execute("SELECT * FROM membres ORDER BY nom").fetchall()
    
    db.close()
    return render_template('membres.html', membres=liste, recherche=recherche)

# ajouter membres
@app.route('/membres/ajouter', methods=['POST'])
def ajouter_membre():
    nom    = request.form['nom'].strip()
    prenom = request.form['prenom'].strip()
    email  = request.form['email'].strip()

    db = get_db()
    # Générer le numéro automatiquement
    dernier = db.execute("SELECT numero FROM membres ORDER BY numero DESC LIMIT 1").fetchone()
    if dernier:
        num = int(dernier['numero'][1:]) + 1
    else:
        num = 1
    numero = f'M{num:04d}'

    try:
        db.execute('INSERT INTO membres VALUES (?, ?, ?, ?)', (numero, nom, prenom, email))
        db.commit()
        flash(f'{prenom} {nom} inscrit(e) avec le numéro {numero}.', 'succès')
    except Exception:
        flash(f"Un membre avec l'email {email} existe déjà.", 'erreur')
    finally:
        db.close()

    return redirect(url_for('membres'))

# supprimer un membre 
@app.route('/membres/supprimer/<numero>', methods=['POST'])
def supprimer_membre(numero):
    db = get_db()
    membre = db.execute('SELECT * FROM membres WHERE numero=?', (numero,)).fetchone()
    if not membre:
        flash('Membre introuvable.', 'erreur')
    else:
        db.execute('DELETE FROM membres WHERE numero=?', (numero,))
        db.commit()
        flash(f'{membre["prenom"]} {membre["nom"]} supprimé(e).', 'succès')
    db.close()
    return redirect(url_for('membres'))


# route pour emprunts
@app.route('/emprunts')
@login_required
def emprunts():
    db = get_db()
    
    recherche  = request.args.get('q', '').strip()
    filtre     = request.args.get('filtre', 'tous')
    aujourd_hui = datetime.now().strftime('%Y-%m-%d')
    
    query = '''
        SELECT e.*, l.titre, m.prenom || ' ' || m.nom AS membre_nom
        FROM emprunts e
        JOIN livres l ON e.isbn_livre = l.isbn
        JOIN membres m ON e.num_membre = m.numero
        WHERE 1=1
    '''
    params = []
    
    if recherche:
        query += ' AND (l.titre LIKE ? OR m.nom LIKE ? OR m.prenom LIKE ? OR e.id LIKE ?)'
        params.extend([f'%{recherche}%'] * 4)
        
    if filtre == 'en_cours':
        query += " AND e.statut = 'en_cours'"
    elif filtre == 'retournes':
        query += " AND e.statut = 'retourne'"
    elif filtre == 'retard':
        query += f" AND e.statut = 'en_cours' AND e.date_retour_prevue < '{aujourd_hui}'"

    query += ' ORDER BY e.date_emprunt DESC'
    liste = db.execute(query, params).fetchall()
    
    livres_dispo = db.execute('SELECT * FROM livres WHERE disponible=1 ORDER BY titre').fetchall()
    tous_membres = db.execute('SELECT * FROM membres ORDER BY nom').fetchall()
    
    db.close()
    return render_template('emprunts.html', emprunts=liste, livres_dispo=livres_dispo, tous_membres=tous_membres,aujourd_hui=aujourd_hui, filtre =filtre, recherche=recherche )


DUREE_EMPRUNT_JOURS = 14

@app.route('/emprunts/emprunter', methods=['POST'])
def emprunter():
    isbn       = request.form['isbn'].strip()
    num_membre = request.form['num_membre'].strip()

    db = get_db()
    livre  = db.execute('SELECT * FROM livres WHERE isbn=?', (isbn,)).fetchone()
    membre = db.execute('SELECT * FROM membres WHERE numero=?', (num_membre,)).fetchone()

    # Vérifier la limite de 3 emprunts
    nb_emprunts = db.execute(
        "SELECT COUNT(*) FROM emprunts WHERE num_membre=? AND statut='en_cours'",
        (num_membre,)
    ).fetchone()[0]

    if nb_emprunts >= 3:
        flash(f'{membre["prenom"]} a atteint la limite de 3 emprunts.', 'error')
    else:
        # Générer l'ID
        dernier = db.execute("SELECT id FROM emprunts ORDER BY id DESC LIMIT 1").fetchone()
        num = int(dernier['id'][3:]) + 1 if dernier else 1
        id_emprunt = f'EMP{num:03d}'

        date_emprunt       = datetime.now().strftime('%Y-%m-%d')
        date_retour_prevue = (datetime.now() + timedelta(days=DUREE_EMPRUNT_JOURS)).strftime('%Y-%m-%d')

        db.execute(
            'INSERT INTO emprunts VALUES (?, ?, ?, ?, ?, NULL, ?)',
            (id_emprunt, isbn, num_membre, date_emprunt, date_retour_prevue, 'en_cours')
        )
        db.execute('UPDATE livres SET disponible=0 WHERE isbn=?', (isbn,))
        db.commit()
        flash(f'Emprunt enregistré ! Retour prévu le {date_retour_prevue}.', 'success')

    db.close()
    return redirect(url_for('emprunts'))


@app.route('/emprunts/retourner', methods=['POST'])
def retourner():
    id_emprunt = request.form['id_emprunt'].strip()

    db = get_db()
    emprunt = db.execute('SELECT * FROM emprunts WHERE id=?', (id_emprunt,)).fetchone()

    date_retour = datetime.now().strftime('%Y-%m-%d')
    db.execute(
        "UPDATE emprunts SET statut='retourne', date_retour_reelle=? WHERE id=?",
        (date_retour, id_emprunt)
    )
    db.execute('UPDATE livres SET disponible=1 WHERE isbn=?', (emprunt['isbn_livre'],))
    db.commit()
    flash('Livre retourné avec succès !', 'success')

    db.close()
    return redirect(url_for('emprunts'))


@app.route('/connexion', methods=['GET', 'POST'])
def connexion():
    if request.method == 'POST':
        email = request.form['email'].strip()
        mot_de_passe = request.form['mot_de_passe'].strip()

        db = get_db()
        utilisateur = db.execute(
            'SELECT * FROM utilisateurs WHERE email=?',
            (email,)
        ).fetchone()
        db.close()

        if utilisateur and check_password_hash(utilisateur['mot_de_passe'],mot_de_passe):
            session['utilisateur_id'] = utilisateur['id']
            session['utilisateur_nom'] = utilisateur['nom']
            session['utilisateur_role'] = utilisateur['role']
            flash(f'Bienvenue {utilisateur["nom"]} !', 'success')
            return redirect(url_for('index'))
        else:
            flash('Email ou mot de passe incorrect.', 'erreur')

    return render_template('connexion.html')


@app.route('/deconnexion')
def deconnexion():
    session.clear()
    flash('Vous avez été déconnecté.', 'success')
    return redirect(url_for('connexion'))

# route utilisateurs 
@app.route('/utilisateurs')
@login_required
@admin_required
def utilisateurs():
    db = get_db()
    liste = db.execute('SELECT * FROM utilisateurs ORDER BY nom').fetchall()
    db.close()
    return render_template('utilisateurs.html', utilisateurs=liste)

@app.route('/utilisateurs/ajouter', methods=['POST'])
@login_required
@admin_required
def ajouter_utilisateur():
    nom          = request.form['nom'].strip()
    email        = request.form['email'].strip()
    mot_de_passe = request.form['mot_de_passe'].strip()
    role         = request.form['role'].strip()

    if not all([nom, email, mot_de_passe, role]):
        flash('Tous les champs sont obligatoires.', 'erreur')
        return redirect(url_for('utilisateurs'))

    db = get_db()
    try:
        db.execute(
            'INSERT INTO utilisateurs VALUES (NULL, ?, ?, ?, ?)',
            (email, generate_password_hash(mot_de_passe), nom, role)
        )
        db.commit()
        flash(f'Compte de {nom} créé avec succès !', 'success')
    except Exception:
        flash(f'Un compte avec l\'email {email} existe déjà.', 'erreur')
    finally:
        db.close()

    return redirect(url_for('utilisateurs'))


@app.route('/utilisateurs/supprimer/<int:id>', methods=['POST'])
@login_required
@admin_required
def supprimer_utilisateur(id):
    db = get_db()
    utilisateur = db.execute('SELECT * FROM utilisateurs WHERE id=?', (id,)).fetchone()

    if utilisateur['role'] == 'admin' and utilisateur['id'] == session['utilisateur_id']:
        flash('Impossible de supprimer votre propre compte admin.', 'erreur')
    else:
        db.execute('DELETE FROM utilisPateurs WHERE id=?', (id,))
        db.commit()
        flash(f'Compte de {utilisateur["nom"]} supprimé.', 'success')

    db.close()
    return redirect(url_for('utilisateurs'))


# catalogue
@app.route('/catalogue')
@login_required
def catalogue():
    db = get_db()
    # Récupérer tous les livres groupés par catégorie
    categories = db.execute(
        'SELECT DISTINCT categorie FROM livres ORDER BY categorie'
    ).fetchall()
    
    livres_par_categorie = {}
    for cat in categories:
        livres_par_categorie[cat['categorie']] = db.execute(
            'SELECT * FROM livres WHERE categorie=? ORDER BY titre',
            (cat['categorie'],)
        ).fetchall()
    
    db.close()
    return render_template('catalogue.html', livres_par_categorie=livres_par_categorie)


if __name__ == '__main__':
    # init_db()
    app.run(debug=True,host='0.0.0.0', port=5000)
    