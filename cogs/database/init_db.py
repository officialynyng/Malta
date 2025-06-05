from cogs.exp_config import engine
from cogs.database.meta import metadata

def init_database():
    metadata.create_all(engine)
