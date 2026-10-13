import os
import subprocess
import sys
from pathlib import Path
from sqlalchemy import create_engine,inspect


def test_migration_upgrade_downgrade(tmp_path):
    env=os.environ.copy();env['DATABASE_URL']='sqlite:///'+(tmp_path/'migration.db').as_posix()
    root=Path(__file__).resolve().parents[1]
    subprocess.run([sys.executable,'-m','alembic','upgrade','head'],cwd=root,env=env,check=True,capture_output=True)
    engine=create_engine(env['DATABASE_URL'])
    assert 'promotion_evidence' in inspect(engine).get_table_names()
    assert 'parser_version' in {c['name'] for c in inspect(engine).get_columns('crawl_results')}
    engine.dispose()
    subprocess.run([sys.executable,'-m','alembic','downgrade','base'],cwd=root,env=env,check=True,capture_output=True)
    engine=create_engine(env['DATABASE_URL'])
    assert 'events' not in inspect(engine).get_table_names()
    engine.dispose()
