"""Configurations Flask par environnement — Séance S5.

Lues depuis les variables d'environnement (aucun secret en dur).
"""
import os


class BaseConfig:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-a-changer-en-prod")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///shellter.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SESSION_COOKIE_HTTPONLY = True          # cookie de session inaccessible au JS
    AGENT_TOKEN = os.getenv("AGENT_TOKEN")

class DevelopmentConfig(BaseConfig):
    DEBUG = True


class TestingConfig(BaseConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False                 # simplifie les tests (POST sans token)
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL", "sqlite+pysqlite:///:memory:"
    )

class IntegrationConfig(BaseConfig):
    """Test local de la stack Docker Compose en HTTP."""
    DEBUG = False
    SESSION_COOKIE_SECURE = False

class ProductionConfig(BaseConfig):
    DEBUG = False
    SESSION_COOKIE_SECURE = True             # cookie envoyé uniquement en HTTPS (S10)


config_by_name = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "integration": IntegrationConfig,
    "production": ProductionConfig,
}