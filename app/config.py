import os

from dotenv import load_dotenv

from app.version import __version__

load_dotenv()


class Settings:
    APP_NAME: str = "solar-meter-bot"
    APP_VERSION: str = os.getenv("APP_VERSION", __version__)
    APP_ENV: str = os.getenv("APP_ENV", "development")
    APP_BASE_URL: str = os.getenv("APP_BASE_URL", "http://localhost:8000")
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Bangkok")

    LINE_CHANNEL_ACCESS_TOKEN: str = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    LINE_CHANNEL_SECRET: str = os.getenv("LINE_CHANNEL_SECRET", "")

    GOOGLE_APPLICATION_CREDENTIALS: str = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
    GOOGLE_SHEETS_SPREADSHEET_ID: str = os.getenv("GOOGLE_SHEETS_SPREADSHEET_ID", "")

    TYPHOON_OCR_API_KEY: str = os.getenv("TYPHOON_OCR_API_KEY", "")

    OCR_RATE_LIMIT_BURST: int = int(os.getenv("OCR_RATE_LIMIT_BURST", "2"))
    OCR_RATE_LIMIT_SUSTAINED: int = int(os.getenv("OCR_RATE_LIMIT_SUSTAINED", "20"))
    OCR_RATE_LIMIT_MAX_RETRIES: int = int(os.getenv("OCR_RATE_LIMIT_MAX_RETRIES", "3"))
    OCR_MAX_PRODUCED_UNIT_KWH: str = os.getenv("OCR_MAX_PRODUCED_UNIT_KWH", "10000")

    IMAGE_DIR: str = os.getenv("IMAGE_DIR", "tmp/images")
    REPORT_DIR: str = os.getenv("REPORT_DIR", "reports")
    REPORT_IMAGE_STORAGE: str = os.getenv("REPORT_IMAGE_STORAGE", "local")

    R2_ENDPOINT: str = os.getenv("R2_ENDPOINT", "")
    R2_ACCESS_KEY_ID: str = os.getenv("R2_ACCESS_KEY_ID", "")
    R2_SECRET_ACCESS_KEY: str = os.getenv("R2_SECRET_ACCESS_KEY", "")
    R2_BUCKET: str = os.getenv("R2_BUCKET", "")
    R2_PUBLIC_URL: str = os.getenv("R2_PUBLIC_URL", "")

    CONFIRMATION_EXPIRY_SECONDS: int = int(os.getenv("CONFIRMATION_EXPIRY_SECONDS", "3600"))

    EXPECTED_METER_COUNT: int = int(os.getenv("EXPECTED_METER_COUNT", "8"))
    DEFAULT_RATE: float = float(os.getenv("DEFAULT_RATE", "4.2"))
    VALID_METER_IDS: list[str] = [
        m.strip() for m in os.getenv("VALID_METER_IDS", "M1,M2,M3,M4,M5,M6,M7,M8").split(",") if m.strip()
    ]
    ADMIN_LINE_USER_IDS: list[str] = [
        item.strip() for item in os.getenv("ADMIN_LINE_USER_IDS", "").split(",") if item.strip()
    ]
    OWNER_LINE_USER_IDS: list[str] = [
        item.strip() for item in os.getenv("OWNER_LINE_USER_IDS", "").split(",") if item.strip()
    ]
    ALLOWED_LINE_SOURCE_IDS: list[str] = [
        item.strip() for item in os.getenv("ALLOWED_LINE_SOURCE_IDS", "").split(",") if item.strip()
    ]


settings = Settings()
