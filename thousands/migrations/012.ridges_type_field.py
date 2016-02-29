from yoyo import step, transaction

transaction(
    step("ALTER TABLE ridges RENAME COLUMN type TO type_")
)
