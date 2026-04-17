"""add xiuxian plugin tables

Revision ID: 20260329_05
Revises: 20260329_04
Create Date: 2026-03-29 20:30:00
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260329_05"
down_revision = "20260329_04"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_settings` (
          `setting_key` VARCHAR(64) NOT NULL,
          `setting_value` JSON NULL,
          `updated_at` DATETIME NOT NULL,
          PRIMARY KEY (`setting_key`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_profiles` (
          `tg` BIGINT NOT NULL,
          `consented` TINYINT(1) NOT NULL DEFAULT 0,
          `root_type` VARCHAR(32) NULL,
          `root_primary` VARCHAR(8) NULL,
          `root_secondary` VARCHAR(8) NULL,
          `root_relation` VARCHAR(16) NULL,
          `root_bonus` INT NOT NULL DEFAULT 0,
          `realm_stage` VARCHAR(32) NOT NULL DEFAULT '凡人',
          `realm_layer` INT NOT NULL DEFAULT 0,
          `cultivation` INT NOT NULL DEFAULT 0,
          `spiritual_stone` INT NOT NULL DEFAULT 0,
          `merit` INT NOT NULL DEFAULT 0,
          `dan_poison` INT NOT NULL DEFAULT 0,
          `breakthrough_pill_uses` INT NOT NULL DEFAULT 0,
          `current_artifact_id` INT NULL,
          `shop_name` VARCHAR(64) NULL,
          `shop_broadcast` TINYINT(1) NOT NULL DEFAULT 0,
          `last_train_at` DATETIME NULL,
          `created_at` DATETIME NOT NULL,
          `updated_at` DATETIME NOT NULL,
          PRIMARY KEY (`tg`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_artifacts` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `name` VARCHAR(64) NOT NULL,
          `rarity` VARCHAR(32) NOT NULL DEFAULT '凡品',
          `image_url` VARCHAR(512) NULL,
          `description` TEXT NULL,
          `power_bonus` INT NOT NULL DEFAULT 0,
          `duel_rate_bonus` INT NOT NULL DEFAULT 0,
          `cultivation_bonus` INT NOT NULL DEFAULT 0,
          `merit_bonus` INT NOT NULL DEFAULT 0,
          `enabled` TINYINT(1) NOT NULL DEFAULT 1,
          `created_at` DATETIME NOT NULL,
          `updated_at` DATETIME NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_xiuxian_artifact_name` (`name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_pills` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `name` VARCHAR(64) NOT NULL,
          `pill_type` VARCHAR(32) NOT NULL,
          `image_url` VARCHAR(512) NULL,
          `description` TEXT NULL,
          `effect_value` INT NOT NULL DEFAULT 0,
          `poison_delta` INT NOT NULL DEFAULT 0,
          `enabled` TINYINT(1) NOT NULL DEFAULT 1,
          `created_at` DATETIME NOT NULL,
          `updated_at` DATETIME NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_xiuxian_pill_name` (`name`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_artifact_inventory` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `tg` BIGINT NOT NULL,
          `artifact_id` INT NOT NULL,
          `quantity` INT NOT NULL DEFAULT 0,
          `created_at` DATETIME NOT NULL,
          `updated_at` DATETIME NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_xiuxian_artifact_inventory` (`tg`, `artifact_id`),
          CONSTRAINT `fk_xiuxian_artifact_inventory_artifact`
            FOREIGN KEY (`artifact_id`) REFERENCES `xiuxian_artifacts` (`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_pill_inventory` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `tg` BIGINT NOT NULL,
          `pill_id` INT NOT NULL,
          `quantity` INT NOT NULL DEFAULT 0,
          `created_at` DATETIME NOT NULL,
          `updated_at` DATETIME NOT NULL,
          PRIMARY KEY (`id`),
          UNIQUE KEY `uq_xiuxian_pill_inventory` (`tg`, `pill_id`),
          CONSTRAINT `fk_xiuxian_pill_inventory_pill`
            FOREIGN KEY (`pill_id`) REFERENCES `xiuxian_pills` (`id`) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_shop_items` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `owner_tg` BIGINT NULL,
          `shop_name` VARCHAR(64) NOT NULL,
          `item_kind` VARCHAR(16) NOT NULL,
          `item_ref_id` INT NOT NULL,
          `item_name` VARCHAR(64) NOT NULL,
          `quantity` INT NOT NULL DEFAULT 0,
          `price_stone` INT NOT NULL DEFAULT 0,
          `enabled` TINYINT(1) NOT NULL DEFAULT 1,
          `is_official` TINYINT(1) NOT NULL DEFAULT 0,
          `created_at` DATETIME NOT NULL,
          `updated_at` DATETIME NOT NULL,
          PRIMARY KEY (`id`),
          KEY `ix_xiuxian_shop_owner` (`owner_tg`),
          KEY `ix_xiuxian_shop_enabled` (`enabled`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS `xiuxian_duel_records` (
          `id` INT NOT NULL AUTO_INCREMENT,
          `challenger_tg` BIGINT NOT NULL,
          `defender_tg` BIGINT NOT NULL,
          `winner_tg` BIGINT NOT NULL,
          `loser_tg` BIGINT NOT NULL,
          `challenger_rate` INT NOT NULL DEFAULT 500,
          `defender_rate` INT NOT NULL DEFAULT 500,
          `summary` TEXT NULL,
          `created_at` DATETIME NOT NULL,
          PRIMARY KEY (`id`),
          KEY `ix_xiuxian_duel_created_at` (`created_at`)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
        """
    )

    op.execute(
        """
        INSERT INTO `xiuxian_settings` (`setting_key`, `setting_value`, `updated_at`)
        VALUES
          ('coin_exchange_rate', '100', CURRENT_TIMESTAMP),
          ('exchange_fee_percent', '1', CURRENT_TIMESTAMP),
          ('min_coin_exchange', '100', CURRENT_TIMESTAMP),
          ('shop_broadcast_cost', '20', CURRENT_TIMESTAMP),
          ('official_shop_name', '"风月阁"', CURRENT_TIMESTAMP)
        ON DUPLICATE KEY UPDATE
          `setting_value` = VALUES(`setting_value`),
          `updated_at` = VALUES(`updated_at`);
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS `xiuxian_duel_records`;")
    op.execute("DROP TABLE IF EXISTS `xiuxian_shop_items`;")
    op.execute("DROP TABLE IF EXISTS `xiuxian_pill_inventory`;")
    op.execute("DROP TABLE IF EXISTS `xiuxian_artifact_inventory`;")
    op.execute("DROP TABLE IF EXISTS `xiuxian_pills`;")
    op.execute("DROP TABLE IF EXISTS `xiuxian_artifacts`;")
    op.execute("DROP TABLE IF EXISTS `xiuxian_profiles`;")
    op.execute("DROP TABLE IF EXISTS `xiuxian_settings`;")
