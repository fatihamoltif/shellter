"""Configurations Flask par environnement — Séance S5.

Lues depuis les variables d'environnement (aucun secret en dur).
"""
import os


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-a-changer-en-prod")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///shellter.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True          # cookie de session inaccessible au JS
    # Cle Fernet pour chiffrer les mots de passe SSH au repos (module d'Imen).
    # En prod : fournie par l'environnement. Defaut dev uniquement.
    INSTANCE_ENCRYPTION_KEY = os.getenv(
        "INSTANCE_ENCRYPTION_KEY",
        "2NC-H59vV-_DzAajvYxi_NnNt66H3AMOX5YK64jFBCk=",
    )


class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False                 # simplifie les tests (POST sans token)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite+pysqlite:///:memory:"
    )


class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True             # cookie envoyé uniquement en HTTPS (S10)


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}
