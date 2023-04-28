from flask import Flask, render_template, request, flash, redirect
from urllib.parse import unquote_plus
from data import db_session
from data.users import User
from data.books import Books
from flask_login import LoginManager, login_required, logout_user, current_user, login_user
from werkzeug.utils import secure_filename
from time import time
from os import path


UPLOAD_FOLDER = './static/books/'
ALLOWED_EXTENSIONS = {'epub', 'fb2', 'mobi', 'kf8', 'azw', 'lrf', 'txt', 'doc', 'docx', 'rtf', 'pdf', 'djvu'}

app = Flask(__name__)

app.config['SECRET_KEY'] = 'tmp_secret_key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def rmparams(query_string, *params_to_remove):
    params = [param.split('=') for param in query_string.split('&')]
    return '&'.join(['='.join(param) for param in params if param[0] not in params_to_remove])


def addparam(query_string, param_to_add, value):
    params = [param for param in query_string.split('&') if param]
    return '&'.join(params + [f'{param_to_add}={value}'])


def getparam(query_string, param_to_get):
    params = [param for param in query_string.split('&') if param]
    param_to_return = [param.split('=')[1] for param in params if param.split('=')[0] == param_to_get]
    return unquote_plus(param_to_return[0]) if param_to_return else ''


@app.route('/', methods=['GET', 'POST'])
def home():
    args = request.args
    sorting_arg, reverse_arg, per_page_arg, page_arg, filterby_arg, filterword_arg = \
        args.get('sort', default='id'), 'r' in args and args.get('r') != '0', args.get('perpage', default='8'), \
        args.get('p', default='0'), args.get('searchby', default='title'), args.get('search', default='')
    
    per_page = int(per_page_arg) if per_page_arg.isdecimal() and int(per_page_arg) >= 1 else 10
    query_string = request.query_string.decode("utf-8")

    db_sess = db_session.create_session()
    library_size = db_sess.query(Books).count()
    
    # Should be replaced later with database functions
    # library_size = 100
    pages_amount = int(library_size / per_page + 0.9)

    page = int(page_arg) if page_arg.isdecimal() and 1 <= int(page_arg) <= pages_amount \
        else 1 if int(page_arg) <= pages_amount else pages_amount
    from datetime import datetime
    books_page = [
        {
        'id': 0,
        'date': str(datetime(2023, 2, 24, 15, 56, 29, 188963)),
        'title': 'Book 0',
        'link': 'https://example.com/',
        'description': 'Example book descrition 0',
        },
        {
        'id': 1,
        'date': str(datetime(2023, 2, 24, 15, 58, 36, 194402)),
        'title': 'Book 1',
        'link': 'https://example.com/',
        'description': 'Example book descrition 1',
        }]

    pages_buttons = \
        [page_button for page_button in \
         [(i + (page - 4 if 4 < page <= pages_amount - 4 else 0 if page < pages_amount - 4 else pages_amount - 7)) \
          if pages_amount >= 7 else i \
          for i in range(1, min(7, pages_amount) + 1)] if page_button > 0 and page_button <= pages_amount] 
    searchby = {'source': 'источнику', 'title': 'названию', 'description': 'описанию'}[filterby_arg]
    
    # books_page = [book | {'img_source': f"{'_'.join(book['link'].split('.')[:2])}.jpg"} for book in books_page]
        
    # Pages usage examples:
    #   http://localhost/?p=0&perpage=15   Page 0 with 15 books on each
    #   http://localhost/?p=5&perpage=2    Page 5 with 2 books on each

    # Sorting examples:
    #   http://localhost/?sort=title  Sorting by 'title'
    #   http://localhost/?sort=title&r=1  Sorting by 'title' with reverse

    return render_template('index.html', books=books_page, pages_buttons=pages_buttons, pages_amount=pages_amount,\
                           searchby=searchby, getparam=getparam, page=page, pagestr=str(page), qs=query_string,\
                           rmparams=rmparams, addparam=addparam, reverse=reverse_arg, current_user=current_user)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.get_id():
        return redirect('/')
    
    if request.method == 'POST':
        login, password = request.form['login'], request.form['password']
        # print(request.form, login, password)
        try:
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.login == login).first()
            check_pass = user.check_password(password)
            # print(user)
            if user and check_pass:
                login_user(user, remember=False)
                return redirect("/")
        except:
            flash(message='Неправильный логин или пароль', category='error')
        return render_template('login.html')
        flash(message='Ошибка проверки данных', category='error')
    return render_template('login.html')


@app.route('/registration', methods=['GET', 'POST'])
def registration():
    if current_user.get_id():
        return redirect('/')
    
    if request.method == 'POST':
        name, surname, login, password, password_repeat = request.form['name'], request.form['surname'], \
            request.form['login'], request.form['password'], request.form['password_repeat']
        print(request.form, name, surname, login, password, password_repeat)
        if password != password_repeat:
            flash(message='Пароли не совпадают!', category='error')
            return render_template('registration.html')
        try:
            user = User()
            user.login = login
            user.name = name
            user.surname = surname
            user.hashed_password = user.hash_password(password)
            db_sess = db_session.create_session()
            db_sess.add(user)
            db_sess.commit()
            flash(message='Регистрация успешна', category='success')
            return redirect('/login')
        except:
            flash(message='Ошибка при добавлении пользователя', category='error')
            return render_template('registration.html')
        
    return render_template('registration.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():    
    if request.method == 'POST':
        title, author, description, genre, created_date = request.form['title'], request.form['author'], \
        request.form['description'], request.form['genre'], request.form['created_date']
        saving_name = str(time()).replace('.', '-', 1)
        print(request.form)
        print(list(request.files.values()))
        file = tuple(request.files.values())[0]
        if file and allowed_file(file.filename):

            db_sess = db_session.create_session()

            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                full_file_name = f'{saving_name}.{filename.rsplit(".", 1)[1]}'
                file.save(path.join(app.config['UPLOAD_FOLDER'], full_file_name))

            book = Books()
            book.title = title
            book.author = author
            book.description = description
            book.genre = genre
            book.created_date = created_date
            book.file_url = f'static/books/{full_file_name}'
            book.user_id = current_user.id

            db_sess.add(book)
            db_sess.commit()
            flash(message='Книга добавлена', category='success')
        
    return render_template('upload.html')


if __name__ == '__main__':
    db_session.global_init("db/data.db")
    # for i in range(3):
    #     user = User()
    #     user.name = f"Пользователь {i}"
    #     user.surname = f"Пользователев {i}"
    #     user.hashed_password = 'password'
    #     db_sess = db_session.create_session()
    #     db_sess.add(user)
    #     db_sess.commit()
    
    # user = db_sess.query(User).filter(User.id == 1).first()
    # books = Books(title="Личная запись1", description="Эта запись личная1")
    # user.books.append(books)
    # db_sess.commit()

    # user = User()
    # db_sess = db_session.create_session()
    # for user in db_sess.query(User).all():
    #     print(user)

    app.run()