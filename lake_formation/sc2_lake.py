"""
Phase 458: AWS Lake Formation - SC2 Data Governance
Register S3 locations, grant column-level permissions, fine-grained access control.
"""

import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

REGION = "us-east-1"
ACCOUNT_ID = "123456789012"
DATA_LAKE_ADMIN = f"arn:aws:iam::{ACCOUNT_ID}:role/SC2DataLakeAdmin"
ANALYST_ROLE = f"arn:aws:iam::{ACCOUNT_ID}:role/SC2Analyst"
BOT_ROLE = f"arn:aws:iam::{ACCOUNT_ID}:role/SC2BotService"

S3_BUCKET = "sc2-data-lake"
S3_BASE_PATH = f"arn:aws:s3:::{S3_BUCKET}"

DATABASE_NAME = "sc2_games_db"
TABLE_GAMES = "games"
TABLE_PLAYERS = "players"
TABLE_REPLAYS = "replays"

# Columns considered PII - analysts see anonymized versions
PII_COLUMNS = ["player_id", "opponent_id", "ip_address"]
OPEN_COLUMNS = [
    "game_id",
    "player_race",
    "map_name",
    "result",
    "apm",
    "mmr",
    "duration_sec",
    "game_date",
]


def get_lakeformation_client():
    return boto3.client("lakeformation", region_name=REGION)


def register_s3_location(lf_client):
    """Register S3 data lake bucket with Lake Formation."""
    try:
        lf_client.register_resource(
            ResourceArn=S3_BASE_PATH,
            UseServiceLinkedRole=False,
            RoleArn=f"arn:aws:iam::{ACCOUNT_ID}:role/LakeFormationServiceRole",
        )
        logger.info(f"Registered S3 location: {S3_BASE_PATH}")
    except ClientError as e:
        if e.response["Error"]["Code"] == "AlreadyExistsException":
            logger.info("S3 location already registered.")
        else:
            raise


def create_database_permissions(lf_client):
    """Grant admin full access to the SC2 database."""
    lf_client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": DATA_LAKE_ADMIN},
        Resource={"Database": {"Name": DATABASE_NAME}},
        Permissions=["ALL"],
        PermissionsWithGrantOption=["ALL"],
    )
    logger.info(f"Granted admin full access to {DATABASE_NAME}.")


def grant_analyst_column_permissions(lf_client):
    """Grant analyst role access to only non-PII columns (anonymized view)."""
    lf_client.grant_permissions(
        Principal={"DataLakePrincipalIdentifier": ANALYST_ROLE},
        Resource={
            "TableWithColumns": {
                "DatabaseName": DATABASE_NAME,
                "Name": TABLE_GAMES,
                "ColumnNames": OPEN_COLUMNS,
            }
        },
        Permissions=["SELECT"],
    )
    logger.info(f"Analyst granted SELECT on columns: {OPEN_COLUMNS}")


def grant_bot_full_table_access(lf_client):
    """Grant bot service full access to games and replays tables."""
    for table in [TABLE_GAMES, TABLE_PLAYERS, TABLE_REPLAYS]:
        lf_client.grant_permissions(
            Principal={"DataLakePrincipalIdentifier": BOT_ROLE},
            Resource={"Table": {"DatabaseName": DATABASE_NAME, "Name": table}},
            Permissions=["SELECT", "INSERT", "DELETE", "ALTER"],
        )
    logger.info(
        f"Bot service granted full access to {[TABLE_GAMES, TABLE_PLAYERS, TABLE_REPLAYS]}."
    )


def apply_data_filter_for_analysts(lf_client):
    """Create a row/column filter so analysts only see anonymized data."""
    lf_client.create_data_cells_filter(
        TableData={
            "TableCatalogId": ACCOUNT_ID,
            "DatabaseName": DATABASE_NAME,
            "TableName": TABLE_GAMES,
            "Name": "analyst_anonymized_view",
            "RowFilter": {"FilterExpression": "result IS NOT NULL"},
            "ColumnNames": OPEN_COLUMNS,
        }
    )
    logger.info("Data cells filter 'analyst_anonymized_view' created.")


def list_permissions(lf_client, table_name: str) -> list:
    """List all permissions on a table."""
    response = lf_client.list_permissions(
        Resource={"Table": {"DatabaseName": DATABASE_NAME, "Name": table_name}},
        MaxResults=100,
    )
    perms = response.get("PrincipalResourcePermissions", [])
    for p in perms:
        logger.info(
            f"  {p['Principal']['DataLakePrincipalIdentifier']}: {p['Permissions']}"
        )
    return perms


def revoke_permissions(
    lf_client, principal_arn: str, table_name: str, permissions: list
):
    """Revoke specific permissions from a principal."""
    lf_client.revoke_permissions(
        Principal={"DataLakePrincipalIdentifier": principal_arn},
        Resource={"Table": {"DatabaseName": DATABASE_NAME, "Name": table_name}},
        Permissions=permissions,
    )
    logger.info(f"Revoked {permissions} from {principal_arn} on {table_name}.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    lf = get_lakeformation_client()
    print("SC2 Lake Formation governance setup.")
    print(f"Database: {DATABASE_NAME}")
    print(f"PII columns (restricted): {PII_COLUMNS}")
    print(f"Open columns (analyst access): {OPEN_COLUMNS}")
    print("Roles: DataLakeAdmin, SC2Analyst (column-level), SC2BotService (full)")
