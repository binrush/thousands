from yoyo import step, transaction

transaction(
    step("ALTER TABLE users DROP COLUMN email"),
    step("ALTER TABLE users RENAME COLUMN img_id TO image_id"),
    step("ALTER TABLE users" +
         "ADD COLUMN preview_id integer REFERENCES images(id)"),
    step("ALTER TABLE users ADD COLUMN location varchar(256)"),
)
