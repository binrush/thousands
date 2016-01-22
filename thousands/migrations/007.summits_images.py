from yoyo import step, transaction

transaction(
    step("""CREATE TABLE summits_images (
        image varchar(64) PRIMARY KEY,
        preview varchar(64) NOT NULL,
        summit_id integer REFERENCES summits(id),
        main boolean DEFAULT false,
        comment text DEFAULT NULL
        )""")
)
