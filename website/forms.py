from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Email, EqualTo, Length
from wtforms import StringField, FloatField, IntegerField, BooleanField, SubmitField, FileField, TextAreaField
from wtforms.validators import DataRequired

# -----------------------------
# SIGNUP FORM
# -----------------------------
class SignupForm(FlaskForm):
    name = StringField("Name", validators=[DataRequired(), Length(min=2, max=50)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField(
        "Confirm Password", validators=[DataRequired(), EqualTo("password")]
    )
    submit = SubmitField("Sign Up")


# -----------------------------
# LOGIN FORM
# -----------------------------
class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Login")


class ShopItemsForm(FlaskForm):
    product_name = StringField("Product Name", validators=[DataRequired()])
    current_price = FloatField("Current Price", validators=[DataRequired()])
    previous_price = FloatField("Previous Price")
    product_picture = FileField("Product Image")
    description = TextAreaField("Description")
    stock = IntegerField("Stock")  # <-- Add this
    submit = SubmitField("Save")

class CategoryForm(FlaskForm):
    name = StringField("Category Name", validators=[DataRequired()])
    submit = SubmitField("Save")
    
class SettingsForm(FlaskForm):
    store_name = StringField("Store Name", validators=[DataRequired()])
    contact_email = StringField("Contact Email", validators=[DataRequired()])
    submit = SubmitField("Save Settings")
