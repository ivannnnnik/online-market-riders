# -*- encoding: utf-8 -*-
import json

from flask import render_template, request, redirect, url_for, flash
from jinja2 import TemplateNotFound
from app import app
from app import db_util
from werkzeug.security import generate_password_hash, check_password_hash
from app import forms
from PIL import Image
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from app.UserLogin import UserLogin
import os
from werkzeug.utils import secure_filename

db = db_util.Database()
login_manager = LoginManager(app)
app.debug = True

login_manager.login_view = 'login'
login_manager.login_message = 'Пожалуйста, авторизуйтесь для продолжения'
login_manager.login_message_category = 'success'


@login_manager.user_loader
def load_user(user_id):
    print('load user')
    return UserLogin().from_db(user_id, db)


@app.route('/user_orders')
def user_orders():
    user_id = current_user.get_id()
    purchases_products = db.get_user_purchases(user_id)
    print(purchases_products)
    if purchases_products:
        context = {
            'purchases_products': purchases_products
        }
        return render_template('user_orders.html', **context)
    else:
        status = 'Ваш список заказов пуст !'
        return render_template('user_orders.html', status=status)


@app.route('/admin_products')
def admin_products():
    user_id = current_user.get_id()
    products = db.get_user_products(user_id)
    # print(products)
    if products:
        context = {
            'products': products,
        }
        return render_template('user_products.html', **context)
    else:
        status = 'У вас нет созданных товаров !'
        return render_template('user_products.html', status=status)


@app.route('/', methods=['GET', 'POST'])
def index():
    products = db.get_products_all()
    if request.method == 'POST':
        if request.form.get('search'):
            products = db.get_products_filter(request.form.get('search'))
        if request.form.get('min'):
            products = [products[i] for i in range(len(products)) if
                        int(products[i]['price']) > int(request.form.get('min'))]
        if request.form.get('max'):
            products = [products[i] for i in range(len(products)) if
                        int(products[i]['price']) < int(request.form.get('max'))]
        if request.form.get('type_product'):
            if request.form.get('type_product') != 'Выберите категорию':
                products = [products[i] for i in range(len(products)) if
                            products[i]['type'] == request.form.get('type_product')]

        if products:
            context = {
                'products': products,
                'count_products': len(products)
            }
            return render_template('index.html', **context)
        else:
            status = True
            return render_template('index.html', status=status)

    if products:
        context = {
            'products': products,
            'count_products': len(products)
        }
        return render_template('index.html', **context)
    else:
        status = True
        return render_template('index.html', status=status)


@app.route('/product/<int:product_id>')
def get_product(product_id):
    products = db.get_product_by_id(product_id)[0]
    print(products)
    return render_template('product.html', product=products)


@app.route('/user_orders/<int:purchase_id>')
def get_products_user_purchase(purchase_id):
    user_id = current_user.get_id()
    products = db.get_products_purchase_by_id(user_id, purchase_id)
    final_price = [products[i]['count_product'] * products[i]['price'] for i in range(len(products))]
    print(final_price)
    if products:
        context = {
            'products': products,
            'count_products': len(products),
            'final_price': sum(final_price)
        }
        return render_template('user_purchase.html', **context)
    else:
        status = True
        return render_template('user_purchase.html', status=status)


@app.route('/registration', methods=['POST', 'GET'])
def register():
    form = forms.RegistrForm()
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        username = request.form.get('name')
        user = db.get_user_by_email(email)
        email = str(email)
        password = str(password)
        username = str(username)
        result = db.create_user(username, email, generate_password_hash(password))
        if result is False:
            status = 'Пользователь с Email уже существует !'
            return render_template('accounts/register.html', form=form, status=status)
        else:
            if result is True:
                status = 'Вы успешно зарегистрировались !'
                return render_template('accounts/login.html', status_true=status)
    return render_template('accounts/register.html', form=form)


@app.route('/authorization', methods=['POST', 'GET'])
def login():
    form = forms.AuthForm
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = False
        if request.form.get("check"):
            remember = True
        user = db.get_user_by_email(email)
        email = str(email)
        password = str(password)
        print(password)
        print(email)
        if user:
            if check_password_hash(user[0]['password'], password):
                user_login = UserLogin().create(user)
                rm = remember
                login_user(user_login, remember=rm)
                return redirect(url_for('index'))
            else:
                status = 'Вы ввели неверный пароль'
                return render_template('accounts/login.html', form=form, status=status)
        else:
            status = 'Вы не зарегистрировались'
            return render_template('accounts/login.html', form=form, status=status)

    return render_template('accounts/login.html', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/new_product', methods=['POST', 'GET'])
@login_required
def new_product():
    form = forms.CreateProduct()
    if request.method =='POST':
        name = request.form.get('name'),
        price = request.form.get('price')
        text = request.form.get('text')
        type_product = request.form.get('type_product')
        photo = request.files['photo']
        name = str(name[0])
        price = str(price)
        text = str(text)
        type_product = str(type_product)
        print(name)
        print(type(name))
        user_id = current_user.get_id()
        filename = secure_filename(photo.filename)
        img_id = db.last_id()
        photo.save(os.path.join(
            app.root_path, 'static\img', f'{img_id}.{filename}'))

        photo_path = os.path.join('static\img', f'{img_id}.{filename}')

        result = db.create_product(name, text, price, user_id, type_product, photo_path)
        if result:
            status = f'Товар {name} успешно создан '
            return render_template('new_product.html', status=status)
        else:
            if result is False:
                status = 'Произошла ошибка'
                return render_template('new_product.html', form=form, status=status)

    return render_template('new_product.html', form=form)


@app.route('/favourite')
@login_required
def favourite_user():
    user_id = current_user.get_id()
    user_fav_products = db.user_favourites(user_id)
    status = 'В избранном ничего нет !'
    if user_fav_products:
        context = {
            'products': user_fav_products,
            'count_products': len(user_fav_products)
        }
        print(user_fav_products)
        return render_template('favourite.html', **context)
    else:
        return render_template('favourite.html', status=status)


@app.route('/cart')
@login_required
def cart_user():
    user_id = current_user.get_id()
    user_cart_products = db.user_cart(user_id)
    status = 'Ваша корзина пуста !'
    if user_cart_products:
        final_price = db.final_price_cart(user_cart_products)
        context = {
            'products': user_cart_products,
            'final_price': final_price
        }
        # print(user_cart_products)
        return render_template('cart.html', **context)
    else:
        return render_template('cart.html', status=status)


@app.route('/profile')
def profile_user():
    user_id = current_user.get_id()
    user_data = db.get_user(user_id)[0]
    context = {
        'id': user_data['id'],
        'username': user_data['name'],
        'email': user_data['email']
    }
    return render_template('profile.html', context=context)


@app.route('/delete_profile')
@login_required
def delete_profile_user():
    user_id = current_user.get_id()
    db.delete_profile_user(user_id)
    return redirect(url_for('logout'))


@app.route("/add_in_cart", methods=['GET', 'POST'])
def add_in_cart_product():
    if request.method == 'GET':
        # print(request.args)
        product_id = int(request.args['product_id'])
        user_id = current_user.get_id()
        if user_id:
            status = db.add_product_in_cart(user_id, product_id)
            if status:
                data = {'response': True}
                return data
            else:
                data = {'response': False}
                return data
        else:
            data = {'response': 'Not auth'}
            return data


@app.route("/add_in_fav", methods=['GET', 'POST'])
def add_in_fav_product():
    if request.method == 'GET':
        # print(request.args)
        product_id = int(request.args['product_id'])
        user_id = current_user.get_id()
        if user_id:
            # print(user_id)
            status = db.add_product_in_favourite(user_id, product_id)
            if status:
                data = {'response': True}
                return data
            else:
                data = {'response': False}
                return data
        else:
            data = {'response': 'Not auth'}
            return data


@app.route("/del_in_cart", methods=['GET', 'POST'])
def del_product_in_cart():
    if request.method == 'GET':
        # print(request.args)
        product_id = int(request.args['product_id'])
        user_id = current_user.get_id()
        status = db.del_product_in_cart(user_id, product_id)
        check_count_product_in_cart = db.user_cart(user_id)
        check_count_product_in_cart = True if check_count_product_in_cart != [] and check_count_product_in_cart != False else 0
        # print('check')
        # print(check_count_product_in_cart)
        if status:
            data = {
                'response': True,
                'id': f'#product-view-class-{product_id}',
                'products': check_count_product_in_cart
            }
            return data
        else:
            data = {'response': False}
            return data


@app.route("/del_in_fav", methods=['GET', 'POST'])
def del_product_in_favourite():
    if request.method == 'GET':
        # print(request.args)
        product_id = int(request.args['product_id'])
        user_id = current_user.get_id()
        status = db.del_product_in_favourite(user_id, product_id)
        if status:
            data = {
                'response': True,
                'id': f'#product-view-class-{product_id}',
            }
            return data
        else:
            data = {'response': False}
            return data


@app.route("/del_in_product", methods=['GET', 'POST'])
def del_admin_product():
    if request.method == 'GET':
        # print(request.args)
        product_id = int(request.args['product_id'])
        status = db.delete_product(product_id)
        if status:
            data = {
                'response': True,
                'id': f'#product-view-class-{product_id}',
            }
            return data
        else:
            data = {'response': False}
            return data


@app.route("/red_product/<int:product_id>")
@login_required
def red_admin_product(product_id):
    product = db.get_product_by_id(product_id)
    product = product[0]
    print(product)
    context = {
        'id': product['id'],
        'name': product['name'],
        'text': product['text'],
        'price': product['price'],
        'type': product['type']
    }
    return render_template('red_product.html', context=context)


@app.route("/red_profile_user", methods=['GET', 'POST'])
@login_required
def red_profile_user():
    user_id = current_user.get_id()
    data_user = db.get_user(user_id)[0]
    context = {
        'id': data_user['id'],
        'name': data_user['name'],
        'email': data_user['email']
    }
    print(context)
    return render_template('red_profile.html', context=context)


@app.route("/update_user_profile", methods=['GET', 'POST'])
@login_required
def update_profile_user():
    user_id = current_user.get_id()
    data_user = db.get_user(user_id)[0]
    context = {
        'name': data_user['name'],
        'email': data_user['email'],
        'password': data_user['password']
    }
    if request.method == 'POST':
        name = request.form.get('name'),
        old_password = request.form.get('old_password'),
        new_password = request.form.get('new_password'),
        name = str(name[0])
        old_password = str(old_password[0])
        new_password = str(new_password[0])
        if name:
            result = db.update_name_user(user_id, name)
            context['name'] = name
            if result is False:
                status = 'Неккоректное Имя'
                return render_template('red_profile.html', status_false=status, context=context)
        if old_password:
            if check_password_hash(context['password'], old_password):
                if new_password:
                    if len(new_password) > 7:
                        if len(new_password) < 45:
                            result = db.update_password_user(user_id, generate_password_hash(new_password))
                            status = 'Данные успешно изменены'
                            return render_template('red_profile.html', status_true=status, context=context)
                        else:
                            status = 'Неккоректный пароль'
                            return render_template('red_profile.html', status_false=status, context=context)
                    else:
                        status = 'Неккоректный пароль'
                        return render_template('red_profile.html', status_false=status, context=context)

                else:
                    status = 'Вы не ввели новый пароль'
                    return render_template('red_profile.html', status_false=status, context=context)
            else:
                status = 'Старый пароль неверный'
                return render_template('red_profile.html', status_false=status, context=context)
        status = 'Данные успешно изменены'
        return render_template('red_profile.html', status_true=status, context=context)
    return render_template('red_profile.html', context=context)


@app.route("/update_product", methods=['GET', 'POST'])
def update_admin_product():
    if request.method == 'POST':
        context = {
            'id': request.form.get('id'),
            'name': request.form.get('name'),
            'text': request.form.get('text'),
            'price': request.form.get('price'),
            'type_product': request.form.get('type_product'),
            'photo': request.files['photo']
        }
        print(context)
        filename = secure_filename(context['photo'].filename)
        photo_path = ""
        if filename != '':
            img_id = db.last_id()
            photo = context['photo']
            photo.save(os.path.join(
                app.root_path, 'static\img', f'{img_id}.{filename}'))
            photo_path = os.path.join('static\img', f'{img_id}.{filename}')

            print(photo_path)
        result = db.update_product(context['id'], context['name'], context['text'], context['price'],
                                   context['type_product'], photo_path)

        return redirect(url_for('admin_products'))


@app.route("/create_order_1", methods=['GET', 'POST'])
def create_order_1():
    if request.method == 'GET':
        user_id = current_user.get_id()
        user_products_in_cart = db.user_cart(user_id)
        user_products_in_cart = {f'{i}': user_products_in_cart[i]['id'] for i in range(len(user_products_in_cart))}
        if user_products_in_cart:
            return user_products_in_cart
        return False


@app.route("/create_order_2", methods=['GET', 'POST'])
def create_order_2():
    if request.method == 'GET':
        user_id = current_user.get_id()
        print(request.args)
        products = dict(request.args)
        if products != {}:
            print(f'Продукты {products}')
            if products:
                # print(products)
                list_product_order = []
                for key_id in products:
                    product_dict = db.get_product_by_id(key_id)
                    count = products[key_id].split()[0]
                    checked = products[key_id].split()[1]
                    list_product_order.append([product_dict, count, checked])
                # print(f'products:   {list_product_order}')
                status = db.add_product_in_order(user_id, list_product_order)
                # print(status)
                context = {
                    'products': list_product_order
                }
                return {}


@app.route("/order", methods=['GET', 'POST'])
def order():
    user_id = current_user.get_id()
    products = db.get_products_in_order(user_id)
    if products:
        final_price = [products[i]['price'] * products[i]['count'] for i in range(len(products))]
        final_price = sum(final_price)
        context = {
            'products': products,
            'final_price': final_price
        }
        return render_template('order.html', **context)
    else:
        status = 'Выберите минимум один товар'
        return render_template('order.html', status_product=status)


@app.route("/payment", methods=['GET', 'POST'])
def payment():
    user_id = current_user.get_id()
    result = db.user_payment_products(user_id)
    for i in range(len(result)):
        db.del_product_in_cart(user_id, int(result[i]['id']))

    status = 'Покупка прошла успешно !'
    return render_template('order.html', status_payment=status)


def pageNotFound(error):
    return render_template('page404.html', title='Страница не найдена !')


if __name__ == '__main__':
    app.run(debug=True)
