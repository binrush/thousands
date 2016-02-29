from yoyo import step, transaction

transaction(
    step("ALTER TABLE ridges ADD COLUMN image varchar(64)"),
    step("ALTER TABLE ridges ADD COLUMN panoram varchar(64)"),
    step("ALTER TABLE ridges ADD COLUMN type text"),
    step("UPDATE ridges SET type='Хребет'")
)
