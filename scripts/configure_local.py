"""Generate local credentials without writing them to terminal output."""
import secrets
from pathlib import Path
root = Path(__file__).resolve().parents[1]
env = root / 'backend' / '.env'
if not env.exists():
    env.write_text('DATABASE_URL=sqlite:///./eventpass.db\nADMIN_TOKEN='+secrets.token_urlsafe(32)+'\nFRONTEND_ORIGIN=http://localhost:3000\nSCHEDULE_MINUTES=0\nTELEGRAM_ENABLED=false\n', encoding='utf-8')
    print('Created backend/.env with a random administrator token. Open the file to copy the token into the dashboard.')
else:
    print('Existing backend/.env preserved.')
