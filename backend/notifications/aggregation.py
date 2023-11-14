def aggregateNotificationsByType(notification_type, notifications_data):
    # dict to store title sets for each user id
    title_users = {}

    for data in notifications_data:
        title = data["title"]
        user_ids = set(data["receiver_user_ids"])

        for user_id in user_ids:
            if user_id in title_users:
                title_users[user_id].add(title)
            else:
                title_users[user_id] = {title}

    # dict looks like this
    print("Title Users Dictionary:")
    for user_id, titles in title_users.items():
        print(f"User ID: {user_id}, Titles: {titles}")

    # aggregate (for now concatenate) all notifications for each user into a single string
    user_notifications = {}
    for user_id, titles in title_users.items():
        user_notifications[user_id] = " + ".join(titles)

    # final result
    print("Final Result:")
    for user_id, notifications in user_notifications.items():
        print(f"User ID: {user_id}, Notifications: {notifications}")


# dummy data to test the notification
notification_type = "publish_project"

notifications_data = [
    {"title": "Notification 1", "receiver_user_ids": [1, 2]},
    {"title": "Notification 2", "receiver_user_ids": [2, 3]},
    {"title": "Notification 3", "receiver_user_ids": [1, 3]},
]

aggregateNotificationsByType(notification_type, notifications_data)
