"""SQLAlchemy ORM models for the biometa database."""
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, String, Text, Integer, Float, Boolean,
    DateTime, ForeignKey, JSON, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Article(Base):
    """PubMed article with all 19 metadata fields."""
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    pmid = Column(String(20), unique=True, nullable=False, index=True)
    title = Column(Text, nullable=False)
    abstract = Column(Text, nullable=True)
    journal = Column(String(512), nullable=True)
    pub_date = Column(String(50), nullable=True)
    doi = Column(String(256), nullable=True)
    language = Column(String(10), nullable=True)
    publication_type = Column(JSON, nullable=True)    # list of strings, stored as JSON
    country = Column(String(100), nullable=True)
    full_text_link = Column(Text, nullable=True)

    # JSON fields for complex data
    authors = Column(JSON, nullable=True)          # [{name, affiliation}, ...]
    affiliations = Column(JSON, nullable=True)     # [string, ...]
    keywords = Column(JSON, nullable=True)         # [string, ...]
    mesh_terms = Column(JSON, nullable=True)       # [string, ...]
    grant_info = Column(JSON, nullable=True)       # [{id, agency}, ...]
    chemical_substances = Column(JSON, nullable=True)  # [string, ...]
    references = Column(JSON, nullable=True)       # [pmid, ...]
    article_ids = Column(JSON, nullable=True)      # {type: id}
    citations_count = Column(Integer, nullable=True)

    # Processing metadata
    embedding = Column(JSON, nullable=True)        # stored as list
    processed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    relationships_as_source = relationship(
        "MicrobeMetaboliteRelationship",
        back_populates="article",
        cascade="all, delete-orphan",
    )

    def __repr__(self):
        return f"<Article pmid={self.pmid} title={self.title[:50]}>"


class Microbe(Base):
    """Microorganism entity."""
    __tablename__ = "microbes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(512), unique=True, nullable=False, index=True)
    normalized_name = Column(String(512), nullable=True)
    microbe_type = Column(String(50), nullable=True)   # bacteria, fungi, virus, archaea
    taxonomy_id = Column(String(50), nullable=True)
    synonyms = Column(JSON, nullable=True)             # [string, ...]
    mention_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    relationships = relationship(
        "MicrobeMetaboliteRelationship", back_populates="microbe"
    )

    def __repr__(self):
        return f"<Microbe {self.name}>"


class Metabolite(Base):
    """Metabolite entity."""
    __tablename__ = "metabolites"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(512), unique=True, nullable=False, index=True)
    normalized_name = Column(String(512), nullable=True)
    chebi_id = Column(String(50), nullable=True)
    pubchem_id = Column(String(50), nullable=True)
    synonyms = Column(JSON, nullable=True)
    metabolite_class = Column(String(100), nullable=True)  # fatty acid, amino acid, etc.
    mention_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    relationships = relationship(
        "MicrobeMetaboliteRelationship", back_populates="metabolite"
    )

    def __repr__(self):
        return f"<Metabolite {self.name}>"


class MicrobeMetaboliteRelationship(Base):
    """Extracted relationship between a microbe and a metabolite."""
    __tablename__ = "relationships"

    id = Column(Integer, primary_key=True, autoincrement=True)
    microbe_id = Column(Integer, ForeignKey("microbes.id"), nullable=False)
    metabolite_id = Column(Integer, ForeignKey("metabolites.id"), nullable=False)
    article_id = Column(Integer, ForeignKey("articles.id"), nullable=False)

    relationship_type = Column(String(50), nullable=False)  # produces, consumes, regulates, inhibits, etc.
    confidence_score = Column(Float, default=0.0)
    evidence_sentence = Column(Text, nullable=True)
    extraction_method = Column(String(50), nullable=True)   # pattern, ner, llm

    created_at = Column(DateTime, default=datetime.utcnow)

    # ORM relationships
    microbe = relationship("Microbe", back_populates="relationships")
    metabolite = relationship("Metabolite", back_populates="relationships")
    article = relationship("Article", back_populates="relationships_as_source")

    __table_args__ = (
        Index("ix_rel_microbe_metabolite", "microbe_id", "metabolite_id"),
        Index("ix_rel_type", "relationship_type"),
    )

    def __repr__(self):
        return f"<Relationship microbe={self.microbe_id} {self.relationship_type} metabolite={self.metabolite_id}>"


class ConversationSession(Base):
    """Stores multi-turn conversation context."""
    __tablename__ = "conversation_sessions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(64), unique=True, nullable=False, index=True)
    messages = Column(JSON, default=list)  # [{role, content}, ...]
    context = Column(JSON, default=dict)   # extracted entities, filters
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
