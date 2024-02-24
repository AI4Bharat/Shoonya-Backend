import os
import json
import redis
import time
from dotenv import load_dotenv

"""
The locks are stored in redis with the format
userid: {
    taskname1:validity,
    taskname2:validity
}
userid is the key in redis, and the python dictionary is stored as a JSON string
"""


class LockException(Exception):
    pass


class Lock:
    def __init__(self, user_id, task_name):
        load_dotenv()
        self.redis_host = os.getenv("REDIS_HOST")
        self.redis_port = os.getenv("REDIS_PORT")
        self.redis_connection = redis.StrictRedis(
            host=self.redis_host, port=self.redis_port, db=0
        )
        self.user_id = user_id
        self.task_name = task_name
        # self.logger = logging.getLogger(f"Lock-{self.user_id}-{self.task_name}")
        # self.logger.setLevel(logging.INFO)

    # Return 1 if the lock is set and 0 if lock is not set
    def lockStatus(self):
        try:
            retrieved_json_str = self.redis_connection.get(self.user_id)
            if retrieved_json_str:
                retrieved_dict = json.loads(retrieved_json_str.decode("utf-8"))
                if self.task_name in retrieved_dict:
                    validity = retrieved_dict[self.task_name]
                    if time.time() > validity:
                        return 0  # Lock has expired
                    else:
                        return 1  # Lock is valid
                else:
                    return 0  # Task name doesn't exist in locks
            else:
                return 0  # user id doesn't exist in Redis
        except Exception as e:
            raise LockException(f"Error setting lock: {str(e)}")

    def setLock(self, timeout):
        try:
            if self.lockStatus() == 0:
                retrieved_json_str = self.redis_connection.get(self.user_id)
                if retrieved_json_str:
                    # JSON for user already exists, append the task name and validity
                    retrieved_dict = json.loads(retrieved_json_str.decode("utf-8"))
                    retrieved_dict[self.task_name] = time.time() + timeout
                    new_json_str = json.dumps(retrieved_dict)
                    self.redis_connection.set(self.user_id, new_json_str)
                    # self.logger.info(f"Lock set for task {self.task_name} and user {self.user_id} for {timeout} seconds")

                else:
                    # create new JSON for redis entry
                    new_dict = {self.task_name: time.time() + timeout}
                    new_json_str = json.dumps(new_dict)
                    self.redis_connection.set(self.user_id, new_json_str)
                    # self.logger.info(f"Lock set for task {self.task_name} and user {self.user_id} for {timeout} seconds")
        except Exception as e:
            raise LockException(f"Error setting lock: {str(e)}")

    def releaseLock(self):
        try:
            if self.lockStatus() == 1:
                retrieved_json_str = self.redis_connection.get(self.user_id)
                retrieved_dict = json.loads(retrieved_json_str.decode("utf-8"))
                if len(retrieved_dict) > 1:
                    del retrieved_dict[self.task_name]
                    new_json_str = json.dumps(retrieved_dict)
                    self.redis_connection.set(self.user_id, new_json_str)
                    # self.logger.info(f"Lock released for task {self.task_name} and user {self.user_id}")
                else:
                    self.redis_connection.delete(self.user_id)
                    # self.logger.info(f"Lock released for task {self.task_name} and user {self.user_id}")
        except Exception as e:
            raise LockException(f"Error releasing lock: {str(e)}")

    def getRemainingTimeForLock(self):
        try:
            if self.lockStatus() == 1:
                retrieved_json_str = self.redis_connection.get(self.user_id)
                retrieved_dict = json.loads(retrieved_json_str.decode("utf-8"))
                remaining_time = retrieved_dict[self.task_name] - time.time()
                return remaining_time
        except Exception as e:
            raise LockException(f"Error getting remaining time for lock: {str(e)}")


# # testing
# if __name__ == '__main__':
#     user_id = "user123"
#     task_name = "task1"
#
#     #test 1
#     lock = Lock(user_id, task_name)
#     print(f"Before setting the lock the lock status is {lock.lockStatus()}")
#
#     lock.setLock(30)
#     print(f"After setting the lock the lock status is {lock.lockStatus()}")
#
#     time.sleep(31)
#     print(f"After waiting 30sec the lock status is {lock.lockStatus()}")
#
#     lock.releaseLock()
#     print(f"after releasing the lock the lock status is {lock.lockStatus()}")
#
#     #test2 part 1
#     lock = Lock(user_id, task_name)
#     print(f"Before setting the lock for 200sec the lock status is {lock.lockStatus()}")
#     lock.setLock(200)
#     print(f"Just after setting the lock for 200sec the lock status is {lock.lockStatus()}")
#
#     #test2 part2
#     lock = Lock(user_id, task_name)
#     print(f"few seconds after setting the lock for 200sec the lock status is {lock.lockStatus()}")
#
#     #test 3 for testing remanining time
#     lock =Lock(user_id,task_name)
#     lock.setLock(100)
#     time.sleep(10)
#     print(f"remaining time = {lock.getRemainingTimeForLock()}")
