#!/bin/bash
set -e

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKUP_DIR="${BASE_DIR}/backups"
TIMESTAMP="$(date +'%Y%m%d_%H%M%S')"
BACKUP_NAME="neural_deck_${TIMESTAMP}.db"
CONTAINER_NAME="english_api"
RETENTION_DAYS=14

mkdir -p "${BACKUP_DIR}"

docker exec "${CONTAINER_NAME}" python3 -c "
import sqlite3
conn = sqlite3.connect('/app/data/neural_deck.db')
conn.execute(\"VACUUM INTO '/app/data/${BACKUP_NAME}'\")
conn.close()
"

mv "${BASE_DIR}/data/${BACKUP_NAME}" "${BACKUP_DIR}/${BACKUP_NAME}"
gzip -9 "${BACKUP_DIR}/${BACKUP_NAME}"
find "${BACKUP_DIR}" -type f -name "neural_deck_*.db.gz" -mtime +${RETENTION_DAYS} -exec rm -f {} \;
