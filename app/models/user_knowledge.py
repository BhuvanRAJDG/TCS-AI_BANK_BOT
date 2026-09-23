from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from .. import db


class UserKnowledge(db.Model):
    __tablename__ = 'user_knowledge'
    __table_args__ = (
        db.Index('ix_user_knowledge_user_id', 'user_id'),
    )

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey('users.id'), nullable=True)
    category   = Column(String(50), default='preference', nullable=False)
    topic      = Column(String(255), nullable=False)
    content    = Column(Text, nullable=False)
    keywords   = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserKnowledge #{self.id} user={self.user_id} topic={self.topic}>"