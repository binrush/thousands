from yoyo import step, transaction

# Removing dummy images downloaded from vk.com as user pictures
# due to bug in vk_get_user and replacing them with NULL to user
# our dummy images instead;

transaction(
    step("UPDATE users SET image=NULL, preview=NULL " +
         "WHERE image='29a62e8bc3609aef88ac2bc722bf7c71f4f86a32.png'"),
    step("DELETE FROM images WHERE " +
         "name='29a62e8bc3609aef88ac2bc722bf7c71f4f86a32.png'"),
    step("DELETE FROM images WHERE " +
         "name='1fc78e0df8d470a82ed55882ac619e7aafa68051.png'")
)
