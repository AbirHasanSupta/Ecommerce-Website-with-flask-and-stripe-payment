from flask_wtf import FlaskForm
from wtforms import SubmitField, StringField, PasswordField, IntegerField
from wtforms.validators import DataRequired


class LoginForm(FlaskForm):
    email = StringField('Enter Your Email', validators=[DataRequired()])
    password = PasswordField("Enter Your Password", validators=[DataRequired()])
    login = SubmitField("LogIn", validators=[DataRequired()])


class RegisterForm(FlaskForm):
    name = StringField('Enter Your Name', validators=[DataRequired()])
    email = StringField('Enter Your Email', validators=[DataRequired()])
    password = PasswordField("Enter Your Password", validators=[DataRequired()])
    login = SubmitField("Sign Up", validators=[DataRequired()])


class ProductForm(FlaskForm):
    name = StringField('Product Name', validators=[DataRequired()])
    price = StringField('Product Price', validators=[DataRequired()])
    category = StringField("Category", validators=[DataRequired()])
    quantity = IntegerField("Quantity")
    image = StringField("Image Link")
    add = SubmitField("Add Product", validators=[DataRequired()])