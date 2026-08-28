from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Response, Cookie, Header, status
from pydantic import BaseModel
import os
import jwt

SECRET_KEY = os.environ.get("MESHCORE_SECRET_KEY", os.environ.get("SECRET_KEY", "CHANGE_ME_TO_A_SECURE_RANDOM_VALUE"))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("MESHCORE_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

class LoginForm(BaseModel):
    username: str
    password: str

router = APIRouter(prefix="/api")

# Replace this with your real user lookup / password hash verification.
def verify_credentials(username: str, password: str) -> Optional[dict]:
    # Example stub — replace with DB lookup / password hash verify.
    if username == "admin" and password == "password":
        return {"username": "admin"}
    return None


def create_access_token(*, data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    token = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    # PyJWT may return bytes in older versions; ensure string
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def get_token_from_cookie_or_header(access_token: Optional[str] = Cookie(None), authorization: Optional[str] = Header(None)):
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    return access_token


def get_current_user(token: str = Depends(get_token_from_cookie_or_header)):
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    payload = decode_token(token)
    username = payload.get("sub")
    if username is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    # Replace with real DB user retrieval
    return {"username": username}


@router.post("/login")
def login(form: LoginForm, response: Response):
    user = verify_credentials(form.username, form.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")
    token = create_access_token({"sub": user["username"]})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        secure=True,     # production: serve over HTTPS
        samesite="lax",
        max_age=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )
    return {"msg": "ok", "username": user["username"]}


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"msg": "logged out"}


@router.get("/me")
def me(current_user = Depends(get_current_user)):
    return {"username": current_user["username"]}
