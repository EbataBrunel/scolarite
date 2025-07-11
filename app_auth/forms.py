from django import forms
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm, PasswordResetForm
from django.contrib.auth.models import User

class UserForm(UserCreationForm):
    class Meta:
        model = User
        fields = [
            'first_name',
            'last_name',
            'username',
            'email',
            'password1',
            'password2'
        ]

        labels = {
            'first_name': 'Votre prénom', 
            'last_name': 'Votre nom ', 
            'username': 'Votre nom utilisateur', 
            'email': 'Votre e-mail', 
            'password1': 'Votre mot de passe',
            'password2': 'Confirmer votre mot de passe'
        }
        
        

        widgets = {
            'last_name': forms.TextInput(attrs={'class':'design', 'required':True}),
            'first_name': forms.TextInput(attrs={'class':'design', 'required':True}),
            'username': forms.TextInput(attrs={'class':'design', 'required':True}),
            'email': forms.TextInput(attrs={'class':'design','required':True}),
            'password1': forms.PasswordInput(attrs={'required':True}),
            'password2': forms.PasswordInput(attrs={'required':True})
            
        }

class LoginForm(forms.Form):
    username = forms.CharField(label="Nom utilisateur", widget=forms.TextInput(attrs={'class':'form-control'}))
    password = forms.CharField(label="Mot de passe", widget=forms.PasswordInput(attrs={'class':'form-control'}))

class PasswordChangingForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for fieldname in ['old_password','new_password1','new_password2']:
            self.fields[fieldname].widget.attrs = {'class':'form-control'}
        
class PasswordResForm(PasswordResetForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for fieldname in ['email']:
            self.fields[fieldname].widget.attrs = {'class':'form-control'}
            
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not User.objects.filter(email=email).exists():
            raise forms.ValidationError("Aucun compte avec cet e-mail n'a été trouvé.")
        return email
            
    
            
           