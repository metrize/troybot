import logging
import json

from pajbot.managers.redis import RedisManager

log = logging.getLogger("pajbot")


class SongRequestQueueManager:

    streamer_name = None
    redis = None
    song_playing_id = None
    song_queues = {}

    @staticmethod
    def init(streamer_name):
        SongRequestQueueManager.streamer_name = streamer_name
        SongRequestQueueManager.redis = RedisManager.get()
        SongRequestQueueManager.song_playing_id = SongRequestQueueManager.redis.get(f"{SongRequestQueueManager.streamer_name}:song-playing-id")
        SongRequestQueueManager.song_queues = {
            "song-queue": SongRequestQueueManager._get_init_redis("song-queue"),
            "backup-song-queue": SongRequestQueueManager._get_init_redis("backup-song-queue")
        }

    @staticmethod
    def force_reload():
        SongRequestQueueManager.song_queues = {
            "song-queue": SongRequestQueueManager._get_init_redis("song-queue"),
            "backup-song-queue": SongRequestQueueManager._get_init_redis("backup-song-queue")
        }

    @staticmethod
    def update_song_playing_id(song_playing_id):
        SongRequestQueueManager.song_playing_id = song_playing_id
        SongRequestQueueManager.redis.set(f"{SongRequestQueueManager.streamer_name}:song-playing-id", song_playing_id)

    @staticmethod
    def inset_song(_id, queue, index=None):
        song_queue = SongRequestQueueManager.song_queues.get(queue, None)
        if song_queue is None:
            log.error(f"invalid queue {queue}")
            return False

        if _id in song_queue:
            log.error(f"Song id {id} already in the queue {queue}")
            return False

        if index:
            song_queue.insert(index, _id)
        else:
            song_queue.append(_id)

        SongRequestQueueManager._update_redis(queue)
        return True

    @staticmethod
    def move_song(from_index, to_index, queue):
        song_queue = SongRequestQueueManager.song_queues.get(queue, None)
        if song_queue is None:
            log.error(f"invalid queue {queue}")
            return False

        if len(song_queue) - 1 < to_index or len(song_queue) - 1 < from_index or (from_index < 0 or to_index < 0 or from_index == to_index):
            log.error(f"invalid queue index")
            return False

        data = song_queue[from_index]
        song_queue.insert(to_index, data)
        song_queue.pop(from_index)

        SongRequestQueueManager._update_redis(queue)
        return True

    @staticmethod
    def remove_song(index, queue):
        song_queue = SongRequestQueueManager.song_queues.get(queue, None)
        if song_queue is None:
            log.error(f"invalid queue {queue}")
            return False

        if len(song_queue) - 1 < index or index < 0:
            return False

        song_queue.pop(index)
        SongRequestQueueManager._update_redis(queue)
        return True

    @staticmethod
    def remove_song_id(_id):
        song_queue = SongRequestQueueManager.song_queues.get("song-queue", None)
        backup_song_queue = SongRequestQueueManager.song_queues.get("backup-song-queue", None)

        if _id in song_queue:
            song_queue.remove(_id)
            SongRequestQueueManager._update_redis("song-queue")
            return True

        if _id in backup_song_queue:
            backup_song_queue.remove(_id)
            SongRequestQueueManager._update_redis("backup-song-queue")
            return True

        return False

    @staticmethod
    def get_id_index(_id):
        song_queue = SongRequestQueueManager.song_queues.get("song-queue", None) + SongRequestQueueManager.song_queues.get("backup-song-queue", None)

        if _id not in song_queue:
            return -1

        return song_queue.index(_id)

    @staticmethod
    def _get_init_redis(name):
        queue = SongRequestQueueManager.redis.get(f"{SongRequestQueueManager.streamer_name}:{name}")
        if queue:
            queue = json.loads(queue)
        else:
            SongRequestQueueManager.redis.set(f"{SongRequestQueueManager.streamer_name}:{name}", "[]")
            queue = []
        return queue

    @staticmethod
    def _update_redis(queue):
        song_queue = SongRequestQueueManager.song_queues.get(queue, None)
        if song_queue is None:
            log.error(f"invalid queue {queue}")
            return
        SongRequestQueueManager.redis.set(f"{SongRequestQueueManager.streamer_name}:{queue}", json.dumps(song_queue))

    @staticmethod
    def _songs_before(_id, queue):
        song_queue = SongRequestQueueManager.song_queues.get(queue, None)
        if song_queue is None:
            log.error(f"invalid queue {queue}")
            return False

        if _id not in song_queue:
            return []

        return song_queue[:song_queue.index(_id)]

    @staticmethod
    def _get_id(index, queue):
        song_queue = SongRequestQueueManager.song_queues.get(queue, None)
        if song_queue is None:
            log.error(f"invalid queue {queue}")
            return False

        if len(song_queue) - 1 < index or index < 0:
            return False

        return song_queue[index]

    @staticmethod
    def get_next_song():
        song_queue = SongRequestQueueManager.song_queues.get("song-queue", None)
        backup_song_queue = SongRequestQueueManager.song_queues.get("backup-song-queue", None)
        return song_queue[0] if len(song_queue) != 0 else (backup_song_queue[0] if len(backup_song_queue) != 0 else None)

    @staticmethod
    def get_next_songs(limit):
        song_queue = SongRequestQueueManager.song_queues.get("song-queue", None)
        backup_song_queue = SongRequestQueueManager.song_queues.get("backup-song-queue", None)
        if not limit:
            return song_queue + backup_song_queue

        if len(song_queue) - 1 < limit:
            limit -= len(song_queue) - 1
            if len(backup_song_queue) - 1 < limit:
                return song_queue + backup_song_queue

            return song_queue + backup_song_queue[:limit]

        else:
            return song_queue[:limit]

    @staticmethod
    def delete_backup_songs():
        SongRequestQueueManager.redis.set(f"{SongRequestQueueManager.streamer_name}:backup-song-queue", "[]")
        SongRequestQueueManager.song_queues["backup-song-queue"] = []
