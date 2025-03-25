from clerk_backend_api import Clerk, models
import jwt
import requests
from jwt.algorithms import RSAAlgorithm
from jwt.exceptions import InvalidTokenError
from asyncio import Lock

# In-memory cache for public keys
public_key_cache = {}
cache_lock = Lock()  # Lock to prevent race conditions while updating the cache


async def get_cached_public_key(jwks_url: str, kid: str):
    """
    Retrieves the public key from the cache or fetches it from the JWKS endpoint if it's not cached.
    :param jwks_url: The URL of the JWKS endpoint.
    :param kid: The key ID to find the public key.
    :return: The public key corresponding to the given `kid`.
    """
    global public_key_cache

    # Check if the public key is in the cache
    if kid in public_key_cache:
        return public_key_cache[kid]

    # Acquire the lock to fetch and update the cache
    async with cache_lock:
        # Double-check if the key was added to the cache during the wait
        if kid in public_key_cache:
            return public_key_cache[kid]

        # Fetch the JWKS data
        response = requests.get(jwks_url)
        if response.status_code != 200:
            raise ConnectionError(f"Failed to fetch JWKS from {jwks_url}: {response.status_code}")

        jwks = response.json()
        keys = jwks.get("keys", [])
        if not keys:
            raise ValueError("No keys found in JWKS.")

        # Find the key with the matching `kid`
        public_key_data = next((key for key in keys if key["kid"] == kid), None)
        if not public_key_data:
            raise ValueError(f"Key with kid `{kid}` not found in JWKS.")

        # Construct the public key
        try:
            public_key = RSAAlgorithm.from_jwk(public_key_data)
        except Exception as e:
            raise ValueError(f"Error constructing public key from JWK: {str(e)}")

        # Update the cache
        public_key_cache[kid] = public_key
        return public_key


async def validate_and_decode_jwt(jwks_url: str,
                                  token: str,
                                  audience: str = None,
                                  issuer: str = None
                                  ):
    """
    Validates and decodes the JWT using a public key retrieved from the JWKS endpoint or cache.

    :param jwks_url: The URL of the JWKS endpoint.
    :param token: The JWT to validate and decode.
    :param audience: Optional audience to validate in the JWT payload.
    :param issuer: Optional issuer to validate in the JWT payload.
    :return: Decoded JWT payload if validation is successful.
    :raises: InvalidTokenError if validation or decoding fails.
    """
    # Decode the header of the JWT to get the `kid` (key ID)
    try:
        unverified_header = jwt.get_unverified_header(token)
        kid = unverified_header.get("kid")
        if not kid:
            raise ValueError("Key ID (kid) missing in the JWT header.")
    except jwt.DecodeError:
        raise InvalidTokenError("Invalid Token: Unable to decode JWT header.")

    # Get the cached public key or fetch it if not cached
    public_key = await get_cached_public_key(jwks_url, kid)

    # Decode and validate the JWT
    try:
        decoded_payload = jwt.decode(
            token,
            public_key,
            algorithms=unverified_header.get("alg"),  # Adjust the algorithm as needed
            audience=audience,
            issuer=issuer,
        )
        return decoded_payload
    except InvalidTokenError as e:
        raise InvalidTokenError(f"Token validation failed: {str(e)}")
    except Exception as e:
        raise ValueError(f"Unexpected error while decoding JWT: {str(e)}")

async def authenticate_user(oauth2_secret_key: str,
                            jwks_url: str,
                            session_token_issuer: str,
                            user_token: str
                            ):
    decoded_jwt = await validate_and_decode_jwt(jwks_url=jwks_url,
                                                token=user_token,
                                                issuer=session_token_issuer
                                                )
    async with Clerk(
            bearer_auth=oauth2_secret_key,
    ) as clerk:
        try:
            user = await clerk.users.get_async(user_id=decoded_jwt.get("sub"))

            return user.email_addresses[0].email_address

        except models.ClerkErrors as e:
            # handle e.data: models.ClerkErrorsData
            raise (e)
        except models.SDKError as e:
            # handle exception
            raise (e)
        except Exception as e:
            raise (e)
