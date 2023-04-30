from flask import Flask, render_template, request, flash, redirect, send_file
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

allowed_params = {
    'sort': ('id', 'title', 'description', 'genre', 'creation_year', 'author'),
    'searchby': ('title', 'description', 'genre', 'author')
}

defalut_params = {
    'sort': 'id',
    'r': '0',
    'perpage': '8',
    'p': '0',
    'searchby': 'title',
    'search': ''
}

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


def get_books_page(start, end, sortby, reverse_arg, filterby, filterword):
    db_sess = db_session.create_session()
    reverse = ('desc' if reverse_arg else 'asc')

    query = (db_sess.query(Books)
             .filter((getattr(Books, filterby).like(f'%{filterword}%') | \
                      (getattr(Books, filterby).like(f'%{filterword.capitalize()}%'))))
             .order_by(getattr(getattr(Books, sortby), reverse)())
             .slice(start, end))

    db_sess.close()
    return [book.__dict__ for book in query]


def get_books_favorite(start, end, sortby, reverse_arg, filterby, filterword, favorite):
    db_sess = db_session.create_session()
    reverse = ('desc' if reverse_arg else 'asc')

    query = (db_sess.query(Books)
             .filter((getattr(Books, filterby).like(f'%{filterword}%') | \
                      (getattr(Books, filterby).like(f'%{filterword.capitalize()}%'))))
             .filter(Books.id.in_(favorite))
             .order_by(getattr(getattr(Books, sortby), reverse)())
             .slice(start, end))

    db_sess.close()
    return [book.__dict__ for book in query]


def trim_string(s):
    if len(s) <= 500:
        return s
    return f'{s[:500 - 1]}…'


@app.route('/favorite', methods=['GET', 'POST'])
@app.route('/', methods=['GET', 'POST'])
def home():
    isfavorite = request.path == '/favorite'
    if isfavorite and not current_user.get_id():
        return redirect('/')
    
    args = request.args
    sorting_arg, reverse_arg, per_page_arg, page_arg, filterby_arg, filterword_arg = \
        args.get('sort', default='id'), 'r' in args and args.get('r') != '0', args.get('perpage', default='8'), \
        args.get('p', default='0'), args.get('searchby', default='title'), str(args.get('search', default=''))
    print(filterword_arg)
    
    sorting_arg = (sorting_arg if sorting_arg in allowed_params['sort'] else defalut_params['sort'])
    filterby_arg = (filterby_arg if filterby_arg in allowed_params['searchby'] else defalut_params['searchby'])
    per_page = int(per_page_arg) if per_page_arg.isdecimal() and int(per_page_arg) >= 1 else 10
    query_string = request.query_string.decode("utf-8")

    db_sess = db_session.create_session()
    library_size = db_sess.query(Books).count()
    db_sess.close()

    pages_amount = int(library_size / per_page + 0.9)
    page = int(page_arg) if page_arg.isdecimal() and 1 <= int(page_arg) <= pages_amount \
        else 1 if int(page_arg) <= pages_amount else pages_amount
    
    if isfavorite:
        favorite = current_user.books_favorited.strip(';').split(';')
        print(favorite)
        books_page = get_books_favorite((page - 1) * per_page, page * per_page,
                                         sorting_arg, reverse_arg, filterby_arg, filterword_arg, favorite)
    else:
        books_page = get_books_page((page - 1) * per_page, page * per_page,
                                     sorting_arg, reverse_arg, filterby_arg, filterword_arg)
    

    pages_buttons = \
        [page_button for page_button in \
         [(i + (page - 4 if 4 < page <= pages_amount - 4 else 0 if page < pages_amount - 4 else pages_amount - 7)) \
          if pages_amount >= 7 else i \
          for i in range(1, min(7, pages_amount) + 1)] if page_button > 0 and page_button <= pages_amount] 
    
    parameters = {'author': 'автору', 'title': 'названию',
                  'description': 'описанию', 'genre': 'жанру',
                  'title': 'названию', 'creation_year': 'году написания'}
        
    # Pages usage examples:
    #   http://localhost/?p=0&perpage=15   Page 0 with 15 books on each
    #   http://localhost/?p=5&perpage=2    Page 5 with 2 books on each

    # Sorting examples:
    #   http://localhost/?sort=title  Sorting by 'title'
    #   http://localhost/?sort=title&r=1  Sorting by 'title' with reverse

    return render_template('index.html', books=books_page, pages_buttons=pages_buttons, pages_amount=pages_amount,\
                           getparam=getparam, page=page, pagestr=str(page), qs=query_string, rmparams=rmparams,\
                           addparam=addparam, reverse=reverse_arg, current_user=current_user, sorting=sorting_arg,\
                           filter=filterby_arg, parameters=parameters, isfavorite=request.path == '/favorite',\
                           trim_string=trim_string)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.get_id():
        return redirect('/')
    
    if request.method == 'POST':
        login, password = request.form['login'], request.form['password']
        try:
            db_sess = db_session.create_session()
            user = db_sess.query(User).filter(User.login == login).first()
            check_pass = user.check_password(password)
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
            user.books_favorited = ''
            db_sess = db_session.create_session()
            db_sess.add(user)
            db_sess.commit()
            db_sess.close()
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
            book.creation_year = created_date
            book.file_url = f'static/books/{full_file_name}'
            book.user_id = current_user.id

            db_sess.add(book)
            db_sess.commit()
            db_sess.close()
            flash(message='Книга добавлена', category='success')
        
    return render_template('upload.html')


@app.route('/book/<int:id>', methods=['GET', 'POST'])
def book(id):

    favorited = f'{id}' in current_user.books_favorited

    if request.method == 'POST':
        enter = request.form['enter']

        if enter == 'download':
            print(request.form)
            file_name = request.form['file_name']
            book_name = request.form['book_name']
            print(file_name)
            directory = path.join(app.root_path, f"{app.config['UPLOAD_FOLDER']}/{file_name}")
            return send_file(directory, as_attachment=True, download_name=f'{book_name}.{file_name.split(".")[-1]}')
        
        elif enter == 'favorite':
            book_id = request.form['book_id']
            try:
                db_sess = db_session.create_session()
                user = db_sess.query(User).filter(User.id == current_user.id).one()
                
                if (not user.books_favorited) or (user.books_favorited and not book_id in user.books_favorited.split(';')):
                    setattr(user, 'books_favorited',
                            ';'.join(user.books_favorited.split(';') + [book_id]) if user.books_favorited else book_id)
                    
                db_sess.commit()
                db_sess.close()
                favorited = True
            except Exception as e:
                print(e)

        elif enter == 'unfavorite':
            book_id = request.form['book_id']
            try:
                db_sess = db_session.create_session()
                user = db_sess.query(User).filter(User.id == current_user.id).one()
                print(book_id)
                print(';'.join([b_id for b_id in user.books_favorited if b_id != book_id]))
                setattr(user, 'books_favorited', ';'.join([b_id for b_id in user.books_favorited if b_id != book_id]))

                db_sess.commit()
                db_sess.close()
                favorited = False
            except Exception as e:
                print(e)

    try:
        db_sess = db_session.create_session()
        book = db_sess.query(Books).filter(Books.id == id).one()
    except Exception as e:
        print(e)
        return "Not found", 404
    print(f'{id}' in current_user.books_favorited)
    
    return render_template('book.html', id=id, book=book, user_id = current_user.get_id(),\
                           favorited=favorited)


if __name__ == '__main__':
    db_session.global_init("db/data.db")
    app.run()
