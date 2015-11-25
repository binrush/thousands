from yoyo import step, transaction

transaction(
    step("ALTER TABLE climbs ADD COLUMN year integer DEFAULT NULL"),
    step("ALTER TABLE climbs ADD COLUMN month integer DEFAULT NULL"),
    step("ALTER TABLE climbs ADD COLUMN day integer DEFAULT NULL"),
    step("UPDATE climbs SET year = EXTRACT(YEAR FROM ts)"),
    step("UPDATE climbs SET month = EXTRACT(MONTH FROM ts)"),
    step("UPDATE climbs SET day = EXTRACT(DAY FROM ts)"),
    step("ALTER TABLE climbs DROP COLUMN ts")
)
