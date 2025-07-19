from pydantic import BaseModel

from workspacex.fulltext.dbs.base import FulltextDB


class FulltextDBConfig(BaseModel):
    provider: str = "elasticsearch"
    config: dict = {}
    
    @classmethod
    def from_config(cls, config: dict):
        if not config:
            return None
        return cls(
            provider=config.get("provider", "elasticsearch"),
            config=config.get("config", {})
        )


class FulltextDBFactory:

    @staticmethod
    def get_fulltext_db(fulltext_db_config: FulltextDBConfig) -> FulltextDB:
        if fulltext_db_config.provider == "elasticsearch":
            from workspacex.fulltext.dbs.elasticsearch import ElasticsearchFulltextDB
            return ElasticsearchFulltextDB(fulltext_db_config.config)
        else:
            raise ValueError(f"Full-text database {fulltext_db_config.provider} is not supported") 