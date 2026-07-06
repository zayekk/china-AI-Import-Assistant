"""
Router API : authentification (inscription, connexion, profil courant).
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.core.security import create_access_token, decode_token
from app.models.user import User
from app.schemas.user import Token, UserCreate, UserLogin, UserOut
from app.services.auth_service import AuthError, authenticate_user, build_tokens, register_user

router = APIRouter(prefix="/auth", tags=["Authentification"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Crée un nouveau compte utilisateur."""
    try:
        user = register_user(db, user_in)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    return user


@router.post("/login", response_model=Token)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """Authentifie un utilisateur et retourne les tokens JWT."""
    try:
        user = authenticate_user(db, credentials.email, credentials.password)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc))
    return build_tokens(user)


@router.post("/refresh", response_model=Token)
def refresh_token(refresh_token: str, db: Session = Depends(get_db)):
    """Génère un nouveau token d'accès à partir d'un refresh token valide."""
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalide ou expiré"
        )

    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Utilisateur invalide")

    return {
        "access_token": create_access_token(user.id),
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=UserOut)
def get_me(current_user: User = Depends(get_current_user)):
    """Retourne le profil de l'utilisateur authentifié."""
    return current_user
