import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env before evaluating Config class
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '.env'), override=True)


class Config:
    # Core Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'sentinelbank-dev-secret-2024')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() in ('true', '1', 'yes')

    # Database: prioritize SQLALCHEMY_DATABASE_URI or DATABASE_URL, default to local SQLite
    SQLALCHEMY_DATABASE_URI = os.getenv(
        'SQLALCHEMY_DATABASE_URI',
        os.getenv('DATABASE_URL', 'sqlite:///sentinelbank.db')
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-jwt-key-dev')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '15')))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '30')))

    # OTP settings
    OTP_EXPIRATION_SECONDS = int(os.getenv('OTP_EXPIRATION_SECONDS', '300'))

    # ChromaDB settings
    CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_data')

    # LLM provider settings
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'gemini')
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')

    # Translation provider settings
    TRANSLATION_PROVIDER = os.getenv('TRANSLATION_PROVIDER', 'mock')
    TRANSLATION_API_KEY = os.getenv('TRANSLATION_API_KEY', '')

    # Misc
    LANGUAGES = ['en', 'kn', 'hi']
    DEFAULT_LANGUAGE = 'en'