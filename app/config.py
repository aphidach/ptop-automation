import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "solar-meter-bot"
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

    IMAGE_DIR: str = os.getenv("IMAGE_DIR", "tmp/images")
    REPORT_DIR: str = os.getenv("REPORT_DIR", "reports")

    CONFIRMATION_EXPIRY_SECONDS: int = int(os.getenv("CONFIRMATION_EXPIRY_SECONDS", "3600"))

    EXPECTED_METER_COUNT: int = int(os.getenv("EXPECTED_METER_COUNT", "8"))
    DEFAULT_RATE: float = float(os.getenv("DEFAULT_RATE", "4.2"))
    VALID_METER_IDS: list[str] = [
        m.strip() for m in os.getenv("VALID_METER_IDS", "M1,M2,M3,M4,M5,M6,M7,M8").split(",") if m.strip()
    ]


settings = Settings()
