import os
from datetime import timedelta

class Config:
    DEBUG = True
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg2://postgres:123@127.0.0.1:5432/finalyear",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "jwt-dev-secret")
    # Increase access token lifetime to reduce frequent expirations during demo
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "e26ba9cde453134c2bb56751ddd0482c")
