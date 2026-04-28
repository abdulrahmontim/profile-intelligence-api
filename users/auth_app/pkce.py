import hashlib
import base64
import secrets



def generate_code_verifier():
    return secrets.token_urlsafe(32)


def generate_code_challenge(verifier):
    digest = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(digest).decode("utf-8").replace("=", "")
    return challenge
    

def generate_state():
    return secrets.token_urlsafe(16)


