# app/models.py
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from .db import Base


class Attorney(Base):
    __tablename__ = "attorneys"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    bar_number = Column(String, index=True)
    state = Column(String, index=True)
    firm = Column(String)
    address = Column(String)
    email = Column(String)
    phone = Column(String)
    last_seen = Column(DateTime)

    cases = relationship("Case", back_populates="attorney")


class Entity(Base):
    __tablename__ = "entities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String)
    sos_id = Column(String, index=True)
    registered_agent = Column(String)
    address = Column(String)

    cases = relationship("Case", back_populates="entity")


class Case(Base):
    __tablename__ = "cases"
    id = Column(Integer, primary_key=True, index=True)
    court = Column(String, index=True)
    case_number = Column(String, index=True)
    case_title = Column(String)
    case_type = Column(String)
    filing_date = Column(Date)
    status = Column(String)
    attorney_id = Column(Integer, ForeignKey("attorneys.id"))
    entity_id = Column(Integer, ForeignKey("entities.id"))
    last_crawled = Column(DateTime)

    attorney = relationship("Attorney", back_populates="cases")
    entity = relationship("Entity", back_populates="cases")
    dockets = relationship("Docket", back_populates="case")


class Docket(Base):
    __tablename__ = "dockets"
    id = Column(Integer, primary_key=True, index=True)
    case_id = Column(Integer, ForeignKey("cases.id"))
    date = Column(Date)
    entry_type = Column(String)
    description = Column(Text)
    document_url = Column(String)

    case = relationship("Case", back_populates="dockets")


class Relationship(Base):
    __tablename__ = "relationships"
    id = Column(Integer, primary_key=True, index=True)
    entity_id = Column(Integer, ForeignKey("entities.id"))
    related_entity_id = Column(Integer, ForeignKey("entities.id"))
    relationship_type = Column(String)


class SearchCache(Base):
    __tablename__ = "search_cache"
    url = Column(String, primary_key=True)
    html = Column(Text)
    timestamp = Column(DateTime)
