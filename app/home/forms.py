from flask_wtf import FlaskForm

from wtforms.fields import StringField, SubmitField, TextAreaField
from wtforms.validators import InputRequired, Length, Email


class ContactForm(FlaskForm):
    email = StringField('Email:',
                        validators=[InputRequired(), Email(message='Please enter your email address.'),
                                    Length(max=30)])
    subject = StringField('Subject:',
                          validators=[InputRequired('Please enter a subject.'), Length(min=1, max=80)])
    message = TextAreaField('Message:', validators=[InputRequired(message=
                                                                  'Please enter a message.'), Length(min=1, max=500)])
    submit = SubmitField('Send')
