from flask import Flask, render_template, request, redirect, url_for
import sqlite3
import os
from hashlib import sha256

app = Flask(__name__)
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 1
app.config['SECRET_KEY'] = 'e2a14f4eecb16a267e5521a7a56b420adfbdbf6f37282995b988de3c1b310f3a'
UPLOAD_FOLDER = 'static/upload'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
DATABASE = 'voting_app.db'

# Database initialization
def initialize_database():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    tables = [
        '''CREATE TABLE IF NOT EXISTS voters (
                id INTEGER PRIMARY KEY,
                name TEXT,
                aadhar_number TEXT,
                iris_mean_value REAL,
                vote_status INTEGER DEFAULT 0
             )''',

        '''CREATE TABLE IF NOT EXISTS parties (
                id INTEGER PRIMARY KEY,
                party_name TEXT,
                logo_image TEXT
             )''',

        '''CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY,
                party_id INTEGER,
                candidate_name TEXT,
                FOREIGN KEY(party_id) REFERENCES parties(id)
             )''',

        '''CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY,
                candidate_id INTEGER,
                FOREIGN KEY(candidate_id) REFERENCES candidates(id)
             )'''
    ]

    for table in tables:
        c.execute(table)

    conn.commit()
    conn.close()

initialize_database()

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form['name']
        aadhar_number = request.form['aadhar_number']
        file = request.files['file']

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)

        with open(file_path, "rb") as f:
            file_bytes = f.read()
            digital_signature = sha256(file_bytes).hexdigest()

        conn = sqlite3.connect(DATABASE)
        c = conn.cursor()

        c.execute('SELECT * FROM voters WHERE aadhar_number=?', (aadhar_number,))
        existing_voter = c.fetchone()

        if not existing_voter:
            conn.close()
            return render_template('login.html', error='Invalid Aadhar number.')
            
        if existing_voter[1] != name:
            conn.close()
            return render_template('login.html', error='Invalid Name')
        elif existing_voter[3] != digital_signature:
            conn.close()
            return render_template('login.html', error='Invalid Digital Signature')
        elif existing_voter[4] != 0:
            conn.close()
            return render_template('login.html', error='Already Voted')
  
        c.execute('''SELECT candidates.id, candidates.candidate_name, parties.party_name, parties.logo_image
                     FROM candidates
                     INNER JOIN parties ON candidates.party_id = parties.id''')
        candidates_data = c.fetchall()

        conn.close()

        return render_template('candidate_list.html', candidates=candidates_data, vname=existing_voter[1], vid=existing_voter[0])

    return render_template('login.html')


@app.route('/admin')
def admin():    
    return render_template('admin.html')
 
@app.route('/admin_home', methods=['GET', 'POST'])
def admin_home():
    if request.method == 'POST':
        id = request.form['id']
        password = request.form['password']
   
        if id == 'admin' and password == 'admin':    
            return render_template('admin.html', error="Login Successful!")
        else:
            return render_template('admin_home.html', error="Invalid ID or Password.")
    return render_template('admin_home.html')

 
@app.route('/logout')
def logout():    
    return render_template('admin_home.html')


@app.route('/vote_candidate/<int:candidate_id>/<int:vid>', methods=['POST'])
def vote_candidate(candidate_id, vid): 
    try:
 
        conn = sqlite3.connect('voting_app.db')
        c = conn.cursor()

        c.execute('INSERT INTO votes (candidate_id) VALUES (?)', (candidate_id,))
        conn.commit()
        
        c.execute('UPDATE voters SET vote_status = 1 WHERE id = ?', (vid,))
        conn.commit()


        conn.close()
        

        return redirect(url_for('login', error="Vote Conducted Successfully"))

    except Exception as e:
        return f"An error occurred: {str(e)}"

  
@app.route('/results')
def results():
    conn = sqlite3.connect('voting_app.db')
    c = conn.cursor()
    

    c.execute('''SELECT candidates.id, candidates.candidate_name, parties.party_name, parties.logo_image, COUNT(votes.id) as vote_count
                 FROM candidates
                 INNER JOIN parties ON candidates.party_id = parties.id
                 LEFT JOIN votes ON candidates.id = votes.candidate_id
                 GROUP BY candidates.id''')
    candidates_votes_data = c.fetchall()

    conn.close()

    return render_template('results.html', candidate_votes=candidates_votes_data)



@app.route('/clear_results', methods=['GET', 'POST'])
def clear_results():
 
        conn = sqlite3.connect('voting_app.db')
        c = conn.cursor()


        c.execute("DELETE FROM votes")
        c.execute("UPDATE voters SET vote_status = 0")

        conn.commit()
        conn.close()

        return redirect(url_for('results'))



from flask import request

@app.route('/add_voter', methods=['GET', 'POST'])
def add_voter():
    if request.method == 'POST':
        name = request.form['name']
        aadhar_number = request.form['aadhar_number'] 
        file = request.files['file']

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        
        with open(file_path, "rb") as f:
            file_bytes = f.read()
            digital_signature = sha256(file_bytes).hexdigest()       

        conn = sqlite3.connect('voting_app.db')
        c = conn.cursor()


        c.execute('SELECT * FROM voters WHERE aadhar_number=?', (aadhar_number,))
        existing_aadhar_voter = c.fetchone()
        if existing_aadhar_voter:
            conn.close()
            return render_template('add_voter.html', error="Aadhar number already exists.")


        c.execute('SELECT * FROM voters WHERE iris_mean_value=?', (digital_signature,))
        existing_iris_voter = c.fetchone()
        if existing_iris_voter:
            conn.close()
            return render_template('add_voter.html', error="Iris already exists.")


        c.execute('INSERT INTO voters (name, aadhar_number, iris_mean_value) VALUES (?, ?, ?)', 
                  (name, aadhar_number, digital_signature))
        conn.commit()
        conn.close()

        return render_template('add_voter.html', error="Voter added successfully!")

    return render_template('add_voter.html')


@app.route('/view_voter', methods=['GET', 'POST'])
def view_voter():
    conn = sqlite3.connect('voting_app.db')
    c = conn.cursor()


    c.execute('SELECT * FROM voters')
    voters = c.fetchall()

    conn.close()


    return render_template('view_voter.html', voters=voters)

@app.route('/delete_voter/<int:voter_id>', methods=['POST'])
def delete_voter(voter_id):
    conn = sqlite3.connect('voting_app.db')
    c = conn.cursor()

    c.execute('DELETE FROM voters WHERE id=?', (voter_id,))
    conn.commit()
    conn.close()


    return redirect(url_for('view_voter'))



@app.route('/add_party', methods=['GET', 'POST'])
def add_party():
    if request.method == 'POST':
        party_name = request.form['party_name']
        file = request.files['file']
        
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
        file.save(file_path)
        

        logo_image = file_path

        conn = sqlite3.connect('voting_app.db')
        c = conn.cursor()


        c.execute('SELECT * FROM parties WHERE party_name=?', (party_name,))
        existing_party = c.fetchone()
        if existing_party:
            conn.close()
            return render_template('add_party.html', error="Party Name Already Exists.")


        c.execute('INSERT INTO parties (party_name, logo_image) VALUES (?, ?)', (party_name, logo_image))
        conn.commit()
        conn.close()

        return render_template('add_party.html', error="Party added successfully!")

    return render_template('add_party.html')


@app.route('/view_party')
def view_party():
    conn = sqlite3.connect('voting_app.db')
    c = conn.cursor()

    c.execute('SELECT * FROM parties')
    parties = c.fetchall()

    conn.close()

    return render_template('view_party.html', parties=parties)

@app.route('/delete_party/<int:party_id>', methods=['POST'])
def delete_party(party_id):
    conn = sqlite3.connect('voting_app.db')
    c = conn.cursor()

    c.execute('DELETE FROM parties WHERE id=?', (party_id,))
    conn.commit()
    conn.close()

    return redirect('/view_party')


@app.route('/add_candidate', methods=['GET', 'POST'])
def add_candidate():
    if request.method == 'POST':
        party_id = request.form['party_id']
        candidate_name = request.form['candidate_name']

        conn = sqlite3.connect('voting_app.db')
        c = conn.cursor()


        c.execute('SELECT * FROM candidates WHERE party_id=?', (party_id,))
        existing_party = c.fetchone()  # Fetch one row

        if existing_party:
            conn.close()
            return render_template('add_candidate.html', error="This party already has a candidate")

        c.execute('INSERT INTO candidates (party_id, candidate_name) VALUES (?, ?)', 
                  (party_id, candidate_name))
        conn.commit()
        conn.close()

        return render_template('add_candidate.html', error="Candidate added successfully!")


    conn = sqlite3.connect('voting_app.db')
    c = conn.cursor()

    c.execute('SELECT * FROM parties')
    parties = c.fetchall()

    conn.close()

    return render_template('add_candidate.html', parties=parties)
    
@app.route('/view_candidate')
def view_candidate():
    try:

        conn = sqlite3.connect('voting_app.db')
        c = conn.cursor()


        c.execute('''SELECT candidates.id, candidates.candidate_name, parties.party_name, parties.logo_image
                     FROM candidates
                     INNER JOIN parties ON candidates.party_id = parties.id''')
        candidates_data = c.fetchall()
        
 
        conn.close()


        return render_template('view_candidate.html', candidates=candidates_data)
    
    except Exception as e:
        return f"An error occurred: {str(e)}"


@app.route('/delete_candidate/<int:candidate_id>', methods=['POST'])
def delete_candidate(candidate_id):

    conn = sqlite3.connect('voting_app.db')
    c = conn.cursor()


    c.execute('DELETE FROM candidates WHERE id=?', (candidate_id,))
    conn.commit()


    conn.close()


    return redirect(url_for('view_candidate'))


if __name__ == '__main__':
    app.run(debug=True)
