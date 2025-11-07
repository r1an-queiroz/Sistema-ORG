# models.py
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class Game(SQLModel, table=True):
    """
    Modelo de dados para armazenar jogos da Steam.
    """
    id: Optional[int] = Field(default=None, primary_key=True)
    appid: Optional[int] = Field(index=True, unique=True, nullable=True)
    title: Optional[str] = Field(default=None, index=True)
    description: Optional[str] = Field(default=None)
    header_image: Optional[str] = Field(default=None)  # URL da imagem
    is_free: Optional[bool] = Field(default=False)
    release_date: Optional[str] = Field(default=None)
    developers: Optional[str] = Field(default=None)  # JSON string
    publishers: Optional[str] = Field(default=None)  # JSON string
    genres: Optional[str] = Field(default=None)      # JSON string
    price_overview: Optional[str] = Field(default=None)  # JSON string (contém currency, final_formatted, etc.)
    raw_json: Optional[str] = Field(default=None)    # backup completo do JSON da Steam
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    local_image_path: Optional[str] = Field(default=None)  # caminho local da imagem (se baixada)

    def __repr__(self):
        return f"<Game(appid={self.appid}, title={self.title})>"