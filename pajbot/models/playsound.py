from sqlalchemy import BOOLEAN, INT, TEXT
from sqlalchemy import Column

from pajbot.managers.db import Base


class Playsound(Base):
    __tablename__ = "playsound"

    name = Column(TEXT, primary_key=True, nullable=False)
    link = Column(TEXT, nullable=False)
    volume = Column(INT, nullable=False, default=100)
    cost = Column(INT, nullable=True)
    cooldown = Column(INT, nullable=True)
    enabled = Column(BOOLEAN, nullable=False, default=True)
