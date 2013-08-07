from wtforms import Form, TextField, PasswordField, validators


class LoginForm(Form):
    username = TextField('Username', [validators.Required()])
    password = PasswordField('Password', [validators.Required()])


class BREFetchForm(Form):
    identifier = TextField("Identifier", [validators.Required()])
    token = PasswordField("Identifier", [validators.Required()])
