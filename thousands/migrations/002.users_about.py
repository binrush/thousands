from yoyo import step, transaction

transaction(
    step("ALTER TABLE users ADD COLUMN about text DEFAULT NULL"),
)
