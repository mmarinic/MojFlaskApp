from flask import Flask, render_template, flash ,redirect ,url_for ,session ,request ,logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps

app = Flask(__name__)
app.secret_key='secret123'
#konfiguriranje MySQL
app.config['MYSQL_HOST']='localhost'
app.config['MYSQL_USER']='root'
app.config['MYSQL_PASSWORD']=''
app.config['MYSQL_DB']='mojflaskapp'
app.config['MYSQL_CURSORCLASS']='DictCursor'
#init MYSQL
mysql=MySQL(app)



#Index
@app.route('/')
def index():
    return render_template('home.html')

#O nama
@app.route('/about')
def about():
    return render_template('about.html')

#Članci
@app.route('/articles')
def articles():
    # Kreiranje cursora
    cur = mysql.connection.cursor()

    # Dobivanje podataka
    result = cur.execute("SELECT * FROM articles")

    articles = cur.fetchall()

    if result > 0:
        return render_template('articles.html', articles=articles)
    else:
        msg = 'No Articles Found'
        return render_template('articles.html', msg=msg)
    # Zatvaranje veze
    cur.close()

#Pojedini članak
@app.route('/article/<string:id>')
def article(id):
    # Kreiranje cursora
    cur = mysql.connection.cursor()

    # Dobivanje podataka
    result = cur.execute("SELECT * FROM articles WHERE id=%s",[id])

    articles = cur.fetchone()

    return render_template('article.html',article=article)

#Forma registracije
class RegisterForm(Form):
    name=StringField('Ime',[validators.Length(min=1,max=50)])
    username=StringField('Korisničko ime', [validators.Length(min=4,max=25)])
    email=StringField('Email',[validators.Length(min=6,max=50)])
    password=PasswordField('Lozinka', [validators.DataRequired(),validators.EqualTo('confirm',message='Lozinke nisu iste')])
    confirm=PasswordField('Potvrdi lozinku')


#Registracija
@app.route('/register',methods=['GET','POST'])
def register():
    form=RegisterForm(request.form)
    if request.method=='POST'and form.validate():
        name=form.name.data
        email=form.email.data
        username=form.username.data
        password=sha256_crypt.encrypt(str(form.username.data))

        #napravljen cursor
        cur =mysql.connection.cursor()
        cur.execute("INSERT INTO users(name,email,username,password) VALUES(%s,%s,%s,%s)",(name,email,username,password))

        #commit to DB
        mysql.connection.commit()

        #zatvara konekciju
        cur.close()
        flash('Sad si registriran i možeš se ulogirat','success')
        return redirect(url_for('login'))
    return render_template('register.html',form=form)

#Korisnicko logiranje
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_candidate = request.form['password']

        cur = mysql.connection.cursor()
        result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

        if result > 0:
            data = cur.fetchone()
            password = data['password']

            if sha256_crypt.verify(password_candidate,password):
                app.logger.info('Lozinka je valjana')
                session['logged_in'] = True
                session['username'] = username

                flash('Sada si ulogiran', 'success')
                return redirect(url_for('dashboard'))
            else:
                error='Nevaljan login'
                app.logger.info('Lozinka nije valjana',error=error)
        else:
            error='Korisničko ime nije nađeno'
            return render_template('login.html',error=error)
    return render_template('login.html')

#Provjeri dali je korisnik login
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Nedozvoljen pristup, Molimo login-ajte se', 'danger')
            return redirect(url_for('login'))
    return wrap


#Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('Sad si logged out','success')
    return redirect(url_for('login'))


#Radna ploča
@app.route('/dashboard')
@is_logged_in
def dashboard():
    #Kreiranje cursora
    cur=mysql.connection.cursor()

    #Dobivanje podataka
    result=cur.execute("SELECT * FROM articles")

    articles=cur.fetchall()

    if result > 0:
        return render_template('dashboard.html',articles=articles)
    else:
        msg='No Articles Found'
        return render_template('dashboard.html',msg=msg)
    #Zatvaranje veze
    cur.close()

#Forma za članke
class ArticleForm(Form):
    title = StringField('Naslov', [validators.Length(min=1,max=200)])
    body = TextAreaField('Sadržaj', [validators.Length(min=30)])

#Dodavanje članaka
@app.route('/add_article',methods=['POST', 'GET'])
@is_logged_in
def add_article():
    form = ArticleForm(request.form)
    if request.method=='POST' and form.validate():
        title=form.title.data
        body=form.body.data

        #kreiranje cursora
        cur=mysql.connection.cursor()

        #Izvršavanje
        cur.execute("INSERT INTO articles(title, body, author) VALUES(%s, %s, %s)",(title,body,session['username']))

        #Ubacivanje u bazu
        mysql.connection.commit()

        #Zatvaranje veze
        cur.close()

        flash('Članak kreiran','success')

        return redirect(url_for('dashboard'))
    return render_template('add_article.html', form=form)

# Uređivanje članka
@app.route('/edit_article/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_article(id):
    # Kreiranje cursor
    cur = mysql.connection.cursor()

    # Uzimanje članka po id-u
    result = cur.execute("SELECT * FROM articles WHERE id = %s", [id])

    article = cur.fetchone()
    cur.close()
    # Uzimanje forme
    form = ArticleForm(request.form)

    # Popunjavanje forme članka
    form.title.data = article['title']
    form.body.data = article['body']

    if request.method == 'POST' and form.validate():
        title = request.form['title']
        body = request.form['body']


        cur = mysql.connection.cursor()
        app.logger.info(title)
        # Izvršavanje
        cur.execute ("UPDATE articles SET title=%s, body=%s WHERE id=%s",(title, body, id))
        # Spremanje u bazu
        mysql.connection.commit()

        #Zatvaranje veze
        cur.close()

        flash('Članak izmjenjen', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

# Brisanje članka
@app.route('/delete_article/<string:id>', methods=['POST'])
@is_logged_in
def delete_article(id):
    # Kreiranje kursora
    cur = mysql.connection.cursor()

    # Izvršavanje
    cur.execute("DELETE FROM articles WHERE id = %s", [id])

    # Spremanje u bazu
    mysql.connection.commit()

    #Zatvaranje veze
    cur.close()

    flash('Članak izbrisan', 'success')

    return redirect(url_for('dashboard'))



if __name__ == '__main__':

    app.run(debug=True)
