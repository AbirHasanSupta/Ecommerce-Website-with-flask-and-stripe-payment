import os
from flask import Flask, render_template, redirect, url_for, flash, abort, request, session
from forms import LoginForm, RegisterForm, ProductForm
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail, Message
from flask_session import Session
import stripe

publishable_key = os.environ['PUBLIC_KEY']

stripe.api_key = os.environ["PRIVATE_KEY"]


app = Flask(__name__)
app.config["SECRET_KEY"] = "blablabla"
Bootstrap5(app)
login_manager = LoginManager()
login_manager.init_app(app)

app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PASSWORD"] = os.environ["MAIL_PASSWORD"]
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.environ["MAIL_USERNAME"]
mail = Mail(app)


@login_manager.user_loader
def load_user(user_id):
    return db.get_or_404(User, user_id)


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
db = SQLAlchemy()
db.init_app(app)


class User(UserMixin, db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    email = db.Column(db.String(250), unique=True, nullable=False)
    password = db.Column(db.String(250), nullable=False)


class Products(db.Model):
    __tablename__ = "Products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(250), nullable=False)
    price = db.Column(db.String(250), nullable=False)
    category = db.Column(db.String(250), nullable=False)
    quantity = db.Column(db.Integer, nullable=True)
    image = db.Column(db.String, nullable=False)


with app.app_context():
    db.create_all()


@app.route('/')
def home():
    products = db.session.execute(db.select(Products)).scalars().all()
    categories = {}
    for product in products:
        category = product.category
        if category not in categories:
            categories[category] = []
        categories[category].append(product)
    sorted_categories = {k: v for k, v in sorted(categories.items(), key=lambda item: item[0])}
    return render_template("index.html", current_user=current_user, categories=sorted_categories)


@app.route("/login", methods=["GET", "POST"])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if user:
            password = form.password.data
            if check_password_hash(user.password, password):
                login_user(user)
                return redirect(url_for("home"))
            else:
                flash("Incorrect Password!Try with proper password.")
        else:
            flash("This Email Does Not Exist. Try again with proper email")
            return redirect(url_for("login"))
    return render_template("login.html", form=form, current_user=current_user)


@app.route("/signup", methods=["GET", "POST"])
def signup():
    form = RegisterForm()
    if form.validate_on_submit():
        user = db.session.execute(db.select(User).where(User.email == form.email.data)).scalar()
        if user:
            flash("Email already exists. Log in Instead")
            return redirect(url_for("login"))
        new_user = User(
            name=form.name.data,
            email=form.email.data,
            password=generate_password_hash(form.password.data, method="pbkdf2:sha256", salt_length=8)
        )
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("registration.html", form=form, current_user=current_user)


@app.route("/logout")
def logout():
    logout_user()
    session.pop("cart", None)
    return redirect(url_for("home"))


@app.route("/products", methods=["GET", "POST"])
def products():
    form = ProductForm()
    if form.validate_on_submit():
        new_product = Products(
            name=form.name.data,
            price=form.price.data,
            category=form.category.data,
            quantity=form.quantity.data,
            image=form.image.data
        )
        db.session.add(new_product)
        db.session.commit()
        return redirect(url_for("products"))
    products = db.session.execute(db.select(Products)).scalars().all()
    return render_template("products.html", form=form, current_user=current_user, products=products)


def admin(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        if not current_user.is_authenticated or current_user.id != 1:
            return abort(403)
        return func(*args, **kwargs)
    return decorated_func


@app.route("/edit/<int:product_id>", methods=["GET", "POST"])
@admin
def edit_product(product_id):
    edit_product = Products.query.get(product_id)
    edit_form = ProductForm(
        name=edit_product.name,
        price=edit_product.price,
        category=edit_product.category,
        quantity=edit_product.quantity,
        image=edit_product.image
    )
    if edit_form.validate_on_submit():
        edit_product.name = edit_form.name.data
        edit_product.price = edit_form.price.data
        edit_product.category = edit_form.category.data
        edit_product.quantity = edit_form.quantity.data
        edit_product.image = edit_form.image.data
        db.session.commit()
        return redirect(url_for("products"))
    return render_template("edit_product.html", form=edit_form, current_user=current_user, product=edit_product)


@app.route("/delete/<int:product_id>", methods=["GET", "POST"])
@admin
def delete_product(product_id):
    product = Products.query.get(product_id)
    db.session.delete(product)
    db.session.commit()
    return redirect(url_for("products"))


@app.route("/cart")
def cart():
    global total
    product_list = session.get("cart", [])
    total = 0
    for item in product_list:
        total += float(item[1].replace("$", ""))
    formatted_total = str("{:.2f}".format(total))
    return render_template("cart.html", product_list=product_list, total=formatted_total)


@app.route("/card-add/<int:product_id>", methods=["GET", "POST"])
def add_to_cart(product_id):
    product = Products.query.get(product_id)
    if not current_user.is_authenticated:
        flash("Please log in to add products to your cart.", "warning")
        return redirect(url_for("login"))
    if product:
        cart_items = session.get("cart", [])
        cart_items.append([product.name, product.price, product.category, product.id])
        session["cart"] = cart_items
    return redirect(url_for("products"))


@app.route("/remove_product/<int:product_id>", methods=["GET", "POST"])
@login_required
def remove_product(product_id):
    cart_items = session.get("cart", [])
    for item in cart_items:
        if item[3] == product_id:
            cart_items.remove(item)
            break
    session["cart"] = cart_items
    return redirect(url_for("cart"))


@app.route("/about")
def about():
    return render_template("about.html")


@app.route("/contact", methods=["GET", "POST"])
def contact():
    if request.method == "POST":
        data = request.form
        msg = Message(subject="New Message from a user of UrbanVogue Emporium", sender=os.environ["MAIL_USERNAME"],
                      recipients=[os.environ["MAIL_USERNAME"]])
        msg.body = f'Name: {data["name"]}\nEmail: {data["email"]}\nPhone: {data["phone"]}\nMessage:{data["message"]}'
        mail.send(msg)
        return render_template("contact.html", msg_sent=True)
    return render_template("contact.html", msg_sent=False)


@app.route("/payment", methods=["POST"])
@login_required
def payment():
    stripe_email = request.form.get('stripeEmail')
    stripe_token = request.form.get('stripeToken')
    amount = request.form.get("amount")

    customer = stripe.Customer.create(
        email=stripe_email,
        source=stripe_token,
    )

    charge = stripe.Charge.create(
        customer=customer.id,
        description='Payment',
        amount=amount,
        currency='usd',
    )
    print(charge)
    return redirect(url_for("thanks"))


@app.route("/thanks")
@login_required
def thanks():
    return render_template("thanks.html")


if __name__ == "__main__":
    app.run(debug=True)
