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
    # "Remember me" on a login form issues a longer-lived token so the
    # device stays signed in across browser restarts.
    REMEMBER_ME_EXPIRE_DAYS: int = 30
    # Forgot-password links are single-use and expire after this long.
    PASSWORD_RESET_EXPIRE_MINUTES: int = 30
    # Public address of the React app. Password-reset emails link here, so
    # it must be set in production (never taken from the request, which an
    # attacker could spoof to steal reset links).
    FRONTEND_URL: str = "http://localhost:3000"

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
    # Also keep a copy of every uploaded screening photo in the database, so
    # photos survive hosts whose local disk is wiped on restart (Hugging
    # Face Spaces, Render free). Leave off when UPLOAD_DIR is persistent.
    STORE_IMAGES_IN_DB: bool = False

    # Inference backend: "torch" runs the .pt checkpoints with Ultralytics;
    # "onnx" runs the exported .onnx models with onnxruntime only (no
    # PyTorch, ~4x less memory) for small hosts. Both give identical boxes.
    YOLO_BACKEND: str = "torch"
    # Built by `python -m app.ml.prepare_onnx` from the .onnx.part* files.
    YOLOV8_ONNX_PATH: str = "models_weights/yolov8_dental.opt.onnx"
    YOLOV12_ONNX_PATH: str = "models_weights/yolov12_dental.opt.onnx"
    # False: load each ONNX model only while it runs (fits 512 MB hosts).
    ONNX_KEEP_LOADED: bool = False
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
    # Cavity is the highest-severity class (it alone triggers the urgent
    # plan), so it gets a stricter floor than the global threshold above.
    CAVITY_CONF_THRESHOLD: float = 0.5
    # In the fused set, keep a cavity only when YOLOv8 AND YOLOv12 both found
    # it. Ignored when only one model is running.
    CAVITY_REQUIRE_AGREEMENT: bool = True
    # Neither model has a braces class, so a metal bracket (a dark, high-
    # contrast square on the tooth) reads as a cavity. A cavity/plaque/tartar
    # box whose pixels are at least this fraction metal-grey is dropped as
    # orthodontic hardware. Enamel, gums and caries score ~0; a tooth box
    # holding a bracket scores ~0.1-0.3.
    METAL_FRACTION_THRESHOLD: float = 0.08

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

    # --- Email (password-reset links) ---
    # Leave SMTP_HOST/SMTP_USER blank to run in log-only mode (see
    # app/notifications.py).
    CLINIC_NAME: str = "CodiSmile Dental Clinic"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@codismile.com"
    SMTP_USE_TLS: bool = True
    SMS_API_KEY: str = ""
    SMS_SENDER_NAME: str = "CodiSmile"

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
