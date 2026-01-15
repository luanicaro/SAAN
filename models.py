from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, Table
from sqlalchemy.orm import relationship
from database import Base
import time

# Tabela de associação para Many-to-Many entre Application e User (Avaliadores)
application_evaluators = Table(
    'application_evaluators', Base.metadata,
    Column('application_id', Integer, ForeignKey('applications.id'), primary_key=True),
    Column('user_id', Integer, ForeignKey('users.id'), primary_key=True)
)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(String)  # admin, engenheiro, stakeholder, avaliador
    
    # Relacionamentos
    forms_created = relationship("Form", back_populates="creator")
    responses_given = relationship("Response", back_populates="evaluator")
    assigned_applications = relationship("Application", secondary=application_evaluators, back_populates="evaluators")

class Form(Base):
    __tablename__ = "forms"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True)
    description = Column(Text, default="")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True) # Pode ser null se migrado de legado sem criador
    
    creator = relationship("User", back_populates="forms_created")
    groups = relationship("QuestionGroup", back_populates="form", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="form", cascade="all, delete-orphan")
    applications = relationship("Application", back_populates="form")
    responses = relationship("Response", back_populates="form")

class QuestionGroup(Base):
    __tablename__ = "question_groups"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"))
    name = Column(String)
    
    form = relationship("Form", back_populates="groups")
    questions = relationship("Question", back_populates="group")

class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    form_id = Column(Integer, ForeignKey("forms.id"))
    group_id = Column(Integer, ForeignKey("question_groups.id"), nullable=True)
    text = Column(Text)
    example = Column(Text, default="")
    scale_type = Column(String, default="5-point")
    
    form = relationship("Form", back_populates="questions")
    group = relationship("QuestionGroup", back_populates="questions")

class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    type = Column(String) # web, mobile
    url = Column(String, default="")
    form_id = Column(Integer, ForeignKey("forms.id"))
    
    form = relationship("Form", back_populates="applications")
    evaluators = relationship("User", secondary=application_evaluators, back_populates="assigned_applications")
    responses = relationship("Response", back_populates="application")
    group_weights = relationship("ApplicationGroupWeight", back_populates="application", cascade="all, delete-orphan")

class ApplicationGroupWeight(Base):
    __tablename__ = "application_group_weights"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    group_id = Column(Integer, ForeignKey("question_groups.id"))
    weight = Column(Float, default=1.0)

    application = relationship("Application", back_populates="group_weights")
    group = relationship("QuestionGroup")

class Response(Base):
    __tablename__ = "responses"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"))
    form_id = Column(Integer, ForeignKey("forms.id"))
    evaluator_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(Integer, default=lambda: int(time.time()))
    
    application = relationship("Application", back_populates="responses")
    form = relationship("Form", back_populates="responses")
    evaluator = relationship("User", back_populates="responses_given")
    answers = relationship("Answer", back_populates="response", cascade="all, delete-orphan")

class Answer(Base):
    __tablename__ = "answers"

    id = Column(Integer, primary_key=True, index=True)
    response_id = Column(Integer, ForeignKey("responses.id"))
    question_id = Column(Integer, ForeignKey("questions.id"))
    value = Column(Integer)
    
    response = relationship("Response", back_populates="answers")
    question = relationship("Question")
