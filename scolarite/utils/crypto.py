from cryptography.fernet import Fernet
from django.conf import settings

fernet = Fernet(settings.FERNET_KEY.encode())

def chiffrer_param(data: str) -> str:
    return fernet.encrypt(data.encode()).decode()

def dechiffrer_param(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
