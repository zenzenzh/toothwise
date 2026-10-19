"""
Central configuration for the Toothwise backend.

All values can be overridden via environment variables (see .env.example).
Keeping configuration in one place is part of our ISO/IEC 25010
"Maintainability - Modularity" story: nothing in the codebase hardcodes
secrets, paths or hosts.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App ---
    APP_NAME: str = "Toothwise AI Screening System"
    ENV: str = "development"
    API_V1_PREFIX: str = "/api"

    # --- Security ---
    SECRET_KEY: str = "change-this-secret-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 12

    def model_post_init(self, __context) -> None:
        """Reject known-weak secrets in production."""
        if self.ENV == "production":
            weak = {"change-this-secret-in-production", ""}
            if self.SECRET_KEY in weak:
                raise ValueError(
                    "SECRET_KEY must be set to a strong random value in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )

    # --- Database ---
    DATABASE_URL: str = "postgresql+psycopg://toothwise:toothwise@db:5432/toothwise"

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:3001,http://127.0.0.1:3001"
    # Also allow any localhost / 127.0.0.1 port, so a dev server that moves
    # to another port (3001, 3002...) is not silently blocked. Set to an
    # empty string in production to allow only CORS_ORIGINS.
    CORS_ORIGIN_REGEX: str = r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$"

    # --- Uploads ---
    UPLOAD_DIR: str = "uploads"
    MAX_UPLOAD_MB: int = 15

    # --- ML models ---
    # If USE_MOCK_MODEL is true (default) the system runs end-to-end with a
    # deterministic, seeded fake detector so the app is fully demoable
    # without needing trained weights yet. Flip to false once you drop your
    # real .pt files into models_weights/.
    USE_MOCK_MODEL: bool = False
    # Set to false to use only YOLOv8 for detection (skips YOLOv12 entirely).
    USE_YOLOV12: bool = True
    # Master switch for ALL AI inference (YOLOv8/YOLOv12 ensemble).
    # When false, screening endpoints answer 503 with a clear
    # message - the rest of the app (patients, records, portal) keeps
    # working. Use this to present the system without the models.
    DETECTION_ENABLED: bool = True
    YOLOV8_WEIGHTS_PATH: str = "models_weights/yolov8_dental.pt"
    YOLOV12_WEIGHTS_PATH: str = "models_weights/yolov12_dental.pt"
    DETECTION_CONF_THRESHOLD: float = 0.25
    ENSEMBLE_IOU_THRESHOLD: float = 0.5

    KNN_MODEL_PATH: str = "app/ml/artifacts/knn_recommender.joblib"
    KNN_NEIGHBORS: int = 5
    # Append-only journal of clinician-confirmed tiers. Each line is one
    # labeled case ({features, tier}) written when a dentist finalizes a
    # screening's tier. The KNN retrains from bootstrap synthetic data plus
    # every case in this file, so real labels accumulate into the model.
    KNN_LABELED_CASES_PATH: str = "app/ml/artifacts/labeled_cases.jsonl"

    # --- Public AI assistant ---
    # Gemini free-tier model for general clinic/dental information only.
    # Never pass patient records or identifiable health information here.
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_TIMEOUT_SECONDS: float = 18.0

    # --- Default seed admin (created on first boot if no dentists exist) ---
    SEED_ADMIN_EMAIL: str = ""
    SEED_ADMIN_PASSWORD: str = ""
    SEED_ADMIN_NAME: str = ""
    SEED_ADMIN_LICENSE: str = ""

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
