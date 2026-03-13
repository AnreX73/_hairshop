from django.contrib.auth.hashers import PBKDF2PasswordHasher

class FastPBKDF2PasswordHasher(PBKDF2PasswordHasher):
    iterations = 130000