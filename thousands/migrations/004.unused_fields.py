from yoyo import step, transaction

transaction(
    step("ALTER TABLE users DROP COLUMN location"),
    step("ALTER TABLE users DROP COLUMN about"),
    step("ALTER TABLE users DROP COLUMN pub")
)
