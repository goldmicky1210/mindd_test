"""SQLAlchemy-based metadata store for startups, documents, and financial metrics."""

from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker

from config import settings


class Base(DeclarativeBase):
    pass


class Startup(Base):
    __tablename__ = "startups"

    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    documents = relationship("Document", back_populates="startup", cascade="all, delete-orphan")
    financial_metrics = relationship("FinancialMetric", back_populates="startup", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True)
    startup_id = Column(String, ForeignKey("startups.id"), nullable=False)
    filename = Column(String, nullable=False)
    doc_type = Column(String, nullable=False)  # "pdf", "excel", "text"
    chunk_count = Column(Float, nullable=True)
    ingested_at = Column(DateTime, default=datetime.utcnow)

    startup = relationship("Startup", back_populates="documents")


class FinancialMetric(Base):
    __tablename__ = "financial_metrics"

    id = Column(String, primary_key=True)
    startup_id = Column(String, ForeignKey("startups.id"), nullable=False)
    metric_name = Column(String, nullable=False)
    value = Column(Float, nullable=True)
    value_text = Column(String, nullable=True)
    unit = Column(String, nullable=True)
    period = Column(String, nullable=True)
    source_file = Column(String, nullable=True)
    extra = Column(JSON, nullable=True)

    startup = relationship("Startup", back_populates="financial_metrics")


def get_engine():
    Path("storage").mkdir(exist_ok=True)
    return create_engine(settings.db_url, connect_args={"check_same_thread": False})


def get_session_factory():
    engine = get_engine()
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


SessionFactory = get_session_factory()


def get_db() -> Session:
    return SessionFactory()


class MetadataStore:
    def __init__(self):
        engine = get_engine()
        Base.metadata.create_all(engine)
        self._Session = SessionFactory

    def upsert_startup(self, startup_id: str, name: str, description: str = "") -> Startup:
        with self._Session() as db:
            startup = db.query(Startup).filter_by(id=startup_id).first()
            if not startup:
                startup = Startup(id=startup_id, name=name, description=description)
                db.add(startup)
            else:
                startup.name = name
                startup.description = description
            db.commit()
            db.refresh(startup)
            return startup

    def get_startup(self, startup_id: str) -> Startup | None:
        with self._Session() as db:
            return db.query(Startup).filter_by(id=startup_id).first()

    def list_startups(self) -> list[dict]:
        with self._Session() as db:
            startups = db.query(Startup).all()
            return [{"id": s.id, "name": s.name, "description": s.description} for s in startups]

    def add_document(self, doc_id: str, startup_id: str, filename: str, doc_type: str, chunk_count: int = 0):
        with self._Session() as db:
            existing = db.query(Document).filter_by(id=doc_id).first()
            if existing:
                existing.chunk_count = chunk_count
                existing.ingested_at = datetime.utcnow()
            else:
                doc = Document(
                    id=doc_id,
                    startup_id=startup_id,
                    filename=filename,
                    doc_type=doc_type,
                    chunk_count=chunk_count,
                )
                db.add(doc)
            db.commit()

    def upsert_financial_metric(
        self,
        metric_id: str,
        startup_id: str,
        metric_name: str,
        value: float | None = None,
        value_text: str | None = None,
        unit: str | None = None,
        period: str | None = None,
        source_file: str | None = None,
        extra: dict[str, Any] | None = None,
    ):
        with self._Session() as db:
            existing = db.query(FinancialMetric).filter_by(id=metric_id).first()
            if existing:
                existing.value = value
                existing.value_text = value_text
                existing.unit = unit
                existing.period = period
                existing.extra = extra
            else:
                metric = FinancialMetric(
                    id=metric_id,
                    startup_id=startup_id,
                    metric_name=metric_name,
                    value=value,
                    value_text=value_text,
                    unit=unit,
                    period=period,
                    source_file=source_file,
                    extra=extra,
                )
                db.add(metric)
            db.commit()

    def get_financial_metrics(self, startup_id: str) -> list[dict]:
        with self._Session() as db:
            metrics = db.query(FinancialMetric).filter_by(startup_id=startup_id).all()
            return [
                {
                    "metric_name": m.metric_name,
                    "value": m.value,
                    "value_text": m.value_text,
                    "unit": m.unit,
                    "period": m.period,
                    "source_file": m.source_file,
                }
                for m in metrics
            ]

    def delete_startup_data(self, startup_id: str):
        """Remove all data for a startup (for re-ingestion)."""
        with self._Session() as db:
            db.query(FinancialMetric).filter_by(startup_id=startup_id).delete()
            db.query(Document).filter_by(startup_id=startup_id).delete()
            db.query(Startup).filter_by(id=startup_id).delete()
            db.commit()


metadata_store = MetadataStore()
