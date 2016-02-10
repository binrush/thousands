from yoyo import step, transaction

transaction(
    step("ALTER TABLE summits ADD COLUMN coordinates point"),
    step("UPDATE summits SET coordinates=point(lat, lng)"),
    step("ALTER TABLE summits DROP COLUMN lat"),
    step("ALTER TABLE summits DROP COLUMN lng"),
    step("ALTER TABLE summits ALTER COLUMN coordinates SET NOT NULL")
)
