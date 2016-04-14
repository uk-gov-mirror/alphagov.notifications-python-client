import calendar
import time

import jwt

from notifications_python_client.errors import (
    TokenDecodeError, TokenExpiredError)

__algorithm__ = "HS256"
__type__ = "JWT"
__bound__ = 30


def create_jwt_token(request_method, request_path, secret, client_id, request_body=None):
    """
    Create JWT token for GOV.UK Notify

    Tokens have standard header:
    {
        "typ": "JWT",
        "alg": "HS256"
    }

    Claims consist of:
    iss: identifier for the client
    iat: issued at in epoch seconds (UTC)
    req: signed request, of the format METHOD PATH. Example POST /resource
    pay: signed payload. Must be the exact value as placed in to request, after any serialization.

    :param request_method: Method of request [GET|POST|etc]
    :param request_path: Path to requested resource
    :param secret: Application signing secret
    :param client_id: Identifier for the client
    :param request_body: Serialized request body, not required. If no request body claim is not set
    :return: JWT token for this request
    """
    assert secret, "Missing secret key"
    assert client_id, "Missing client id"

    headers = {
        "typ": __type__,
        "alg": __algorithm__
    }

    claims = {
        'iss': client_id,
        'iat': epoch_seconds()
    }

    return jwt.encode(payload=claims, key=secret, headers=headers).decode()


def get_token_issuer(token):
    """
    Issuer of a token is the identifier used to recover the secret
    Need to extract this from token to ensure we can proceed to the signature validation stage
    Does not check validity of the token
    :param token: signed JWT token
    :return issuer: iss field of the JWT token
    :raises AssertionError: is iss field not present
    """
    try:
        unverified = decode_token(token)
        assert 'iss' in unverified
        return unverified['iss']
    except jwt.DecodeError:
        raise TokenDecodeError("Invalid token")


def decode_jwt_token(token, secret, request_method, request_path, request_payload=None):
    """
    Validates and decodes the JWT token
    Token checked for
        - signature of JWT token
        - token issued date is valid

    :param token: jwt token
    :param secret: client specific secret
    :param request_method: HTTP method for the request
    :param request_path: Resource path for the request
    :param request_payload: Body of the request
    :return boolean: True if valid token, False otherwise
    :raises AssertionError: If any required fields are not present
    :raises jwt.DecodeError: If signature validation fails
    """
    try:
        # check signature of the token
        decoded_token = jwt.decode(
            token,
            key=secret.encode(),
            verify=True,
            algorithms=[__algorithm__],
            leeway=__bound__
        )

        # token has all the required fields
        assert 'iss' in decoded_token, 'Missing iss field in token'
        assert 'iat' in decoded_token, 'Missing iat field in token'

        # check iat time is within bounds
        now = epoch_seconds()
        iat = int(decoded_token['iat'])

        if now > (iat + __bound__):
            raise TokenExpiredError("Token has expired", decoded_token)

        return True
    except jwt.InvalidIssuedAtError:
        raise TokenExpiredError("Token has invalid iat field", decode_token(token))
    except jwt.DecodeError:
        raise TokenDecodeError("Invalid token")


def decode_token(token):
    """
    Decode token but don;t check the signature
    :param token:
    :return decoded token:
    """
    return jwt.decode(token, verify=False, algorithms=[__algorithm__])


def epoch_seconds():
    return calendar.timegm(time.gmtime())
