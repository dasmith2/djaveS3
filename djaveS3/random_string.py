import secrets
import string


def random_string(length=7):
  choices = string.ascii_uppercase + string.digits
  return ''.join(secrets.choice(choices) for _ in range(length))
