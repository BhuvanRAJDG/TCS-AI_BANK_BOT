import os
from datetime import timedelta

class Config:
    # Core Flask settings
    SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-please')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() in ('true', '1', 'yes')

    # Database
    # Database — evaluated when create_app() calls from_object() so env overrides work
    @staticmethod
    def _db_url():
        return os.getenv(
            'SQLALCHEMY_DATABASE_URI',
            os.getenv('DATABASE_URL',
                      'mysql+pymysql://sentinel_user:sentinel_pass@db:3306/sentinelbank')
        )

    SQLALCHEMY_DATABASE_URI = property(lambda self: Config._db_url()) if False else \
        os.getenv('SQLALCHEMY_DATABASE_URI',
                  os.getenv('DATABASE_URL',
                            'mysql+pymysql://sentinel_user:sentinel_pass@db:3306/sentinelbank'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # JWT settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'super-secret-jwt-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=int(os.getenv('JWT_ACCESS_MINUTES', '15')))
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=int(os.getenv('JWT_REFRESH_DAYS', '30')))

    # OTP settings
    OTP_EXPIRATION_SECONDS = int(os.getenv('OTP_EXPIRATION_SECONDS', '300'))  # 5 minutes

    # ChromaDB settings
    CHROMA_PERSIST_DIRECTORY = os.getenv('CHROMA_PERSIST_DIRECTORY', './chroma_data')

    # LLM provider settings (example for OpenAI)
    LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'openai')
    LLM_API_KEY = os.getenv('LLM_API_KEY', '')

    # Translation provider settings
    TRANSLATION_PROVIDER = os.getenv('TRANSLATION_PROVIDER', 'mock')
    TRANSLATION_API_KEY = os.getenv('TRANSLATION_API_KEY', '')

    # Misc
    LANGUAGES = ['en', 'kn', 'hi']
    DEFAULT_LANGUAGE = 'en'
