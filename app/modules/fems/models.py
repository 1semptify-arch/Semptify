"""FEMS SQLAlchemy models — extends Semptify's database."""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base
from app.core.utc import utc_now


class FemsCase(Base):
    __tablename__ = "fems_cases"

    id = Column(Integer, primary_key=True, index=True)
    case_number = Column(String(100), unique=True, nullable=False)
    title = Column(String(500))
    status = Column(String(50), default="active")
    opened_at = Column(DateTime, default=lambda: utc_now())

    documents = relationship("FemsDocument", back_populates="case", cascade="all, delete-orphan")


class FemsDocument(Base):
    __tablename__ = "fems_documents"

    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("fems_cases.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    file_type = Column(String(50))
    file_hash = Column(String(64), unique=True, index=True)
    file_size = Column(BigInteger, default=0)
    extracted_text = Column(Text)
    ingested_at = Column(DateTime, default=lambda: utc_now())

    case = relationship("FemsCase", back_populates="documents")
    chunks = relationship("FemsChunk", back_populates="document", cascade="all, delete-orphan")
    phone_links = relationship("FemsDocumentPhone", back_populates="document", cascade="all, delete-orphan")


class FemsChunk(Base):
    __tablename__ = "fems_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("fems_documents.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)

    document = relationship("FemsDocument", back_populates="chunks")


class FemsPhoneNumber(Base):
    __tablename__ = "fems_phone_numbers"

    id = Column(Integer, primary_key=True, index=True)
    number = Column(String(50), unique=True, nullable=False, index=True)
    label = Column(String(200))
    first_seen = Column(DateTime, default=lambda: utc_now())

    doc_links = relationship("FemsDocumentPhone", back_populates="phone", cascade="all, delete-orphan")


class FemsDocumentPhone(Base):
    """Many-to-many link between documents and phone numbers."""

    __tablename__ = "fems_document_phones"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("fems_documents.id"), nullable=False)
    phone_id = Column(Integer, ForeignKey("fems_phone_numbers.id"), nullable=False)

    document = relationship("FemsDocument", back_populates="phone_links")
    phone = relationship("FemsPhoneNumber", back_populates="doc_links")


class FemsQuarantineFile(Base):
    __tablename__ = "fems_quarantine"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    file_hash = Column(String(64), index=True)
    file_size = Column(BigInteger, default=0)
    reason = Column(String(200), default="duplicate")
    quarantined_at = Column(DateTime, default=lambda: utc_now())
