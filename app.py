from flask import Flask, render_template, redirect, flash, request, url_for, session, g
from flask_session import Session
import os, random, string, pathlib, requests
import sqlite3 as sql
from werkzeug.utils import secure_filename
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import timedelta, date
from tempfile import mkdtemp

app = Flask(__name__)

#define image folder for guitars
abpath = os.path.dirname(os.path.abspath(__file__))
path = '/static/guitars/'
app.config['GUITAR_FOLDER'] = (abpath + path)
# SESSION KEY
size = 50
sessionkey = ''.join(random.choices(string.ascii_uppercase + string.ascii_lowercase + string.punctuation + string.hexdigits + string.digits, k = size))
app.secret_key = sessionkey
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
Session(app)

# HOME PAGE
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
def index():

    # set image for masthead
    imgs = os.listdir(abpath + '/static/imgs')
    rand = (random.sample(imgs, 1))
    for i in rand:
        img = "/static/imgs/" + str(i)

    #gallery = os.listdir(path)
    con = sql.connect(abpath + '/blankc.db')
    con.row_factory = sql.Row
    cur = con.cursor()
    cur.execute('SELECT photos.photo, guitars.* FROM guitars LEFT OUTER JOIN photos ON guitars.serial = photos.serial WHERE "primary" = "yes" ORDER BY guitars.serial ASC')
    gallery = cur.fetchall()

    with open(abpath + '/static/about.txt') as f:
        about = str(f.read())

    if request.method == "POST":

        #text entries
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']
        today = date.today()

        con.execute('INSERT INTO msgs (name, email, phone, message, date) VALUES (?, ?, ?, ?, ?)', (name, email, phone, message, today))
        con.commit()

        flash('Message has been sent!')
        return render_template('/index.html', img = img, gallery = gallery, about = about)

    return render_template('/index.html', img = img, gallery = gallery, about = about)

@app.route('/details', methods=['GET', 'POST'])
def details():

    if request.method == "POST":

        serial = request.form['lookup']

        #gallery = os.listdir(path)
        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute('SELECT photos.photo, guitars.* FROM guitars LEFT OUTER JOIN photos ON guitars.serial = photos.serial WHERE guitars.serial = ?', (serial,))
        gallery = cur.fetchall()
        cur.execute('SELECT * FROM guitars WHERE serial = ?', (serial,))
        info = cur.fetchall()

        return render_template('/details.html', gallery = gallery, info = info)

    return render_template('/details.html')

@app.route('/msg', methods=['GET', 'POST'])
def msg():
    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute('SELECT * FROM msgs ORDER BY msgid DESC')
        msgs = cur.fetchall()

        if request.method == "POST":
            deletethis = request.form

            for i in deletethis:
                delete = i
                print(delete)

                con.execute("DELETE FROM msgs WHERE msgid = ?", (delete,))
                con.commit()

            return redirect('/msg')

        return render_template('msg.html', msgs = msgs)

    else:
        crumb = '/msg'
        return render_template("/login.html", crumb = crumb)

@app.route('/register', methods=['GET', 'POST'])
def register():

    con = sql.connect(abpath + '/blankc.db')
    con.row_factory = sql.Row
    cur = con.cursor()
    if request.method == "POST":

        #text entries
        name = request.form['name']
        email = request.form['email'].lower()
        password = request.form['password']
        confirm = request.form['confirm']

        #name and password validation
        chars = ['$', '#', '@', '!', '*', '.']
        if not name:
            flash('Name is required!')
            return render_template('/register.html')
        elif not password:
            flash('Password is required!')
            return render_template('/register.html')
        elif not confirm:
            flash('Password confirmation is required!')
            return render_template('/register.html')
        elif confirm != password:
            flash('Passwords do not match!')
            return render_template('/register.html')
        #password complexity check
        elif len(password) < 7:
            flash('The password must be 7 characters or longer.')
            return render_template('/register.html')
        elif not any (c in chars for c in password):
            flash("Password must contain one of the following... " + str(chars))
            return render_template('/register.html')

        #check to see if email is in use
        cur.execute('SELECT email FROM users WHERE email = ?', (email,))
        dupe = bool(cur.fetchall())
        if dupe is True:
            flash('email already in use.')
            return render_template('/register.html')

        else:
            password = generate_password_hash(password)
            con.execute('INSERT INTO users (name, email, hash) VALUES (?, ?, ?)', (name, email, password))
            con.commit()
            flash('account created')
            return redirect('/panel')

    return render_template('/register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')
    else:
        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()

        session.clear()

        if request.method == "POST":
            #session.pop('user', None)
            email = request.form['email'].lower()
            password = request.form['password']
            crumb = request.form['crumb']
            #user validation
            if not email:
                flash('Email is required!')
                return render_template('/login.html')
            # Ensure password was submitted
            elif not password:
                flash("Must provide password!")
                return render_template('/login.html')
            else:
                dbhash = cur.execute('SELECT hash FROM users WHERE email = ?', (email,))
                for i in dbhash:
                    dbhash = i[0]
                verify = check_password_hash(dbhash, password)
                if verify is False:
                    flash('Your password did not match.')
                    return render_template('/login.html')
                else:

                    session['user'] = email
                    print(crumb)
                    return redirect(crumb)

        return redirect('/panel')

# ADMIN INVENTORY MANAGEMENT
@app.route('/inv', methods=['GET', 'POST'])
def inventory():
    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute('SELECT * FROM guitars')
        rows = cur.fetchall()

        if request.method == "POST":
            deletethis = request.form

            for i in deletethis:
                delete = i
                cur.execute('SELECT photo FROM photos WHERE serial = ?', (delete,))
                # query pulls up the path of the photo from the photo column for deletion in loop.
                for j in cur.fetchall():
                    os.remove(abpath + j[0])

                con.execute("DELETE FROM guitars WHERE serial = ?", (delete,))
                con.commit()
                con.execute("DELETE FROM photos WHERE serial = ?", (delete,))
                con.commit()

            return redirect('/inv')

        return render_template('inv.html', rows = rows)

    else:
        crumb = '/inv'
        return render_template("/login.html", crumb = crumb)

@app.route('/edit', methods=['GET', 'POST'])
def edit():

    if request.method == "POST":

        serial = request.form['edit']

        #gallery = os.listdir(path)
        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute('SELECT photos.photo, guitars.* FROM guitars LEFT OUTER JOIN photos ON guitars.serial = photos.serial WHERE guitars.serial = ?', (serial,))
        gallery = cur.fetchall()
        cur.execute('SELECT * FROM guitars WHERE serial = ?', (serial,))
        info = cur.fetchall()

        return render_template('/edit.html', gallery = gallery, info = info)

    return redirect('/inv')

@app.route('/editphoto', methods=['GET', 'POST'])
def editphoto():

    if request.method == "POST":

        serial = request.form['edit']

        #gallery = os.listdir(path)
        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute('SELECT photos.photo, guitars.* FROM guitars LEFT OUTER JOIN photos ON guitars.serial = photos.serial WHERE guitars.serial = ?', (serial,))
        gallery = cur.fetchall()
        cur.execute('SELECT * FROM guitars WHERE serial = ?', (serial,))
        info = cur.fetchall()

        return render_template('/editphoto.html', gallery = gallery, info = info)

    return redirect('/inv')

@app.route('/editsubmit', methods=['GET', 'POST'])
def editsubmit():

    if request.method == "POST":
        edit = request.form['edit']
        name = request.form['name']
        summary = request.form['summary']
        about = request.form['about']
        price = request.form['price']
        serial = request.form['serial']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()

        con.execute('UPDATE guitars SET (name, summary, about, price, serial) = (?, ?, ?, ?, ?) WHERE serial = ?', (name, summary, about, price, serial, edit))
        con.commit()
        con.execute('UPDATE photos SET serial = ? WHERE serial = ?', (serial, edit))
        con.commit()
        #gallery = os.listdir(path)
        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute('SELECT photos.photo, guitars.* FROM guitars LEFT OUTER JOIN photos ON guitars.serial = photos.serial WHERE guitars.serial = ?', (serial,))
        gallery = cur.fetchall()
        cur.execute('SELECT * FROM guitars WHERE serial = ?', (serial,))
        info = cur.fetchall()
        
        flash('records updated')
        return render_template('/edit.html', gallery = gallery, info = info)

    return redirect('/inv')

@app.route('/add', methods=['GET', 'POST'])
def add():
    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        if request.method == "POST":

            photo = []
            #text entries
            name = request.form['name'].lower()
            serial = request.form['serial'].upper()
            price = request.form['price']
            about = request.form['about']
            summary = request.form['summary']

            cur.execute('SELECT serial FROM guitars WHERE serial = ?', (serial,))
            dupe = cur.fetchall()

            if dupe != []:
                message = "An entry already exists for serial # " + serial
                flash(message)
                return render_template('/add.html')
            else:
                photos = os.listdir(abpath + path)

                con.execute('INSERT INTO guitars (name, serial, price, about, summary) VALUES (?, ?, ?, ?, ?)', (name, serial, price, about, summary))
                con.commit()

                for photo in request.files.getlist('photo'):
                    prefix = name + serial
                    photo.save(os.path.join(abpath + path, prefix + '-' + photo.filename))
                    photopath = str(os.path.join(path, prefix + '-' + photo.filename))

                    #add to photo database
                    con.execute('INSERT INTO photos (serial, photo) VALUES (?, ?)', (serial, photopath))
                    con.commit()

                cur.execute('SELECT photo FROM photos WHERE photo = ? LIMIT 1;', (photopath,))
                primarypic = cur.fetchone()

                con.execute("UPDATE photos SET 'primary' = (?) WHERE photo = (?)", ('yes', photopath,))
                con.commit()

                flash('upload successful')
                return render_template('/add.html')
        return render_template("/add.html")
    else:
        crumb = '/add'
        return render_template("/login.html", crumb = crumb)

@app.route('/panel', methods=['GET', 'POST'])
def panel():

    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

    else:
        crumb = '/panel'
        return render_template("/login.html", crumb = crumb)

    with open(abpath + '/static/about.txt') as f:
        about = str(f.read())

    con = sql.connect(abpath + '/blankc.db')
    con.row_factory = sql.Row
    cur = con.cursor()
    cur.execute("SELECT * FROM users")
    usrs = cur.fetchall()

    return render_template('/panel.html', about = about, usrs = usrs)

@app.route('/aboutedit', methods=['GET', 'POST'])
def aboutedit():
    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

    aboutedit = request.form['aboutedit']
    con = sql.connect(abpath + '/blankc.db')
    con.row_factory = sql.Row
    cur = con.cursor()

    if request.method == "POST":
        f = open('static/about.txt', 'w')
        f.truncate(0)
        f.write(aboutedit)
        f.close()
    with open('static/about.txt') as f:
        about = str(f.read())
        flash('update successful')
        return redirect('/panel')

@app.route('/usrmod', methods=['GET', 'POST'])
def usrmod():
    if 'user' in session:
        user = session['user']
        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

    usrlist = request.form

    con = sql.connect(abpath + '/blankc.db')
    con.row_factory = sql.Row
    cur = con.cursor()
    if request.method == "POST":
        for i in usrlist:
            usr = i
        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (usr,))
        edit = cur.fetchall()
        cur.execute("SELECT * FROM users WHERE email = ? AND status = 'admin'", (usr,))
        toggle = cur.fetchall()
        if toggle == []:
            toggle = 'admin'
        else:
            toggle = 'normal'

        return render_template('/accounts.html', edit = edit, toggle = toggle)

@app.route('/modify', methods=['GET', 'POST'])
def modify():
    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

    con = sql.connect(abpath + '/blankc.db')
    con.row_factory = sql.Row
    cur = con.cursor()

    if request.method == "POST":

        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form['confirm']
        status = request.form['status']

        if password != "":

            #name and password validation
            chars = ['$', '#', '@', '!', '*', '.']
            if not name:
                flash('Name is required!')

            elif not password:
                flash('Password is required!')

            elif not confirm:
                flash('Password confirmation is required!')

            elif confirm != password:
                flash('Passwords do not match!')

            #password complexity check
            elif len(password) < 7:
                flash('The password must be 7 characters or longer.')

            elif not any (c in chars for c in password):
                flash("Password must contain one of the following... " + str(chars))
                return render_template("/panel.html")
            else:
                password = generate_password_hash(password)
                con.execute('UPDATE users SET hash = ? WHERE email = ?', (password, email))
                con.commit()
        else:
            con.execute('UPDATE users SET (name, status) = (?, ?) WHERE email = ?', (name, status, email))
            con.commit()

        flash('Account changed successfully!')
        return redirect('/panel')

    return render_template('/accounts.html')

@app.route('/delusr', methods=['GET', 'POST'])
def delusr():
    if 'user' in session:
        user = session['user']

        con = sql.connect(abpath + '/blankc.db')
        con.row_factory = sql.Row
        cur = con.cursor()
        cur.execute("SELECT email FROM users WHERE email = ? AND status = 'admin'", (user,))
        authusrs = cur.fetchall()

        if authusrs == []:
            return redirect('/logout')

    con = sql.connect(abpath + '/blankc.db')
    con.row_factory = sql.Row
    cur = con.cursor()

    if request.method == "POST":
        remove = request.form['remove']
        email = request.form['email']

        if remove != "":
            if email == user:
                flash('Deleting your own account will destroy the time-space continuum. Please reconsider.')
                return redirect('/panel')
            else:
                con.execute('DELETE FROM users WHERE email = ?', (email,))
                con.commit()
                flash('User has been removed.')
            return redirect('/panel')

    return render_template('/accounts.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('logged out')
    return redirect('/login')