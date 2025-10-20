from bson import ObjectId
from dotenv import load_dotenv

from brokerservice.model import CourseDetails, VideoDetails
from brokerservice.status import Status
from databaseservice.databaseService import database_service
from loggingConfig import logger
from videoindexerclient.model import Video

load_dotenv()

class BrokerRepository:
    """
    BrokerRepository is a Repository Class that interacts with Azure CosmosDB via PyMongo.
    Interacts with video and course collection.

    Args:
        video_collection (str): Name of Video Collection. Default: "video".
        course_collection (str): Name of Course Collection. Default: "course.
    """

    def __init__(
            self,
            video_collection: str = "video",
            course_collection: str = "course"
    ):
        db = database_service.get_db()
        self.video = db[video_collection]
        self.course = db[course_collection]

    def insert_video_indexing_progress(self, video: Video, course_id: ObjectId):
        """
        Insert Video to Video Collection and update Course with video ID.

        Args:
            video (VideoDetails): Number of seconds. Required.
            course_id (ObjectId): Object ID of Course. Required.

        Returns:
            ObjectId: video_id
        """
        document = {
            "name": video.video_name,
            "status": Status.IN_PROGRESS.value,
            "course_reference_id": course_id,
            "video_description": video.video_description
        }
        video_id = self.video.insert_one(document).inserted_id

        filter_query = {"_id": course_id}
        update_data = {
            "$push": {"videos": video_id}
        }
        result = self.course.update_one(filter_query, update_data)
        if result.matched_count > 0:
            logger.info("Document updated successfully for insert_video_indexing_progress.")
            return video_id
        else:
            logger.info("Document update failed for insert_video_indexing_progress.")
            return ""

    def update_video_id_thumbnail(self, video_object_id: ObjectId, video_id: str, video_thumbnail: str):
        filter_query = {"_id": video_object_id}

        new_fields = {
            "video_id": video_id,
            "thumbnail": "data:image/jpeg;base64," + video_thumbnail
        }
        result = self.video.update_one(filter_query, {"$set": new_fields})
        if result.matched_count > 0:
            print("Video Document Thumbnail updated successfully.")
        else:
            print("No matching Video Document found.")

    def change_video_status(self, video_object_id: ObjectId, status_new: Status):
        filter_query = {"_id": video_object_id}

        new_fields = {
            "status": status_new.value,
            "visibility": "PRIVATE"
        }
        result = self.video.update_one(filter_query, {"$set": new_fields})
        if result.matched_count > 0:
            logger.info("Video Status updated successfully for ID: " + str(video_object_id))
        else:
            logger.info("No matching document found for ID: " + str(video_object_id))
            raise Exception("No matching document found for ID: " + str(video_object_id))

    def check_if_course_exist(self, course_code: str) -> dict:
        """
        Check if Course Code exist in Course collection.

        Args:
            course_code (str): Course Code. Required.

        Returns:
            dict: Course Document.
        """
        filter_query = {"course_code": course_code}

        result = self.course.find_one(filter_query)
        if result:
            logger.info("Course exist for Course Code: " + str(course_code))
            return result
        else:
            logger.info("Course does not exist for Course Code: " + str(course_code))
            return {}

    def update_visibility_option_course(self, course_id, visibility):
        filter_query = {"course_code": course_id}
        visibility_update = {"visibility": visibility}
        result = self.course.update_one(filter_query, {"$set": visibility_update})
        if result.matched_count > 0:
            print("Course Document Visibility updated successfully.")
            return result.upserted_id
        else:
            print("No matching document found.")

    def update_visibility_option_video(self, video_id, visibility):
        filter_query = {"video_id": video_id}
        visibility_update = {"visibility": visibility}
        result = self.video.update_one(filter_query, {"$set": visibility_update})
        if result.matched_count > 0:
            print("Video Document Visibility updated successfully.")
            return result.upserted_id
        else:
            print("No matching document found.")

    def update_course_details(self, course_details: CourseDetails):
        filter_query = {"course_code": course_details.course_id}
        course_update = {"course_name": course_details.course_name, "summary": course_details.course_description}
        result = self.course.update_one(filter_query, {"$set": course_update})
        if result.matched_count > 0:
            print("Course Document updated successfully for Course Code: ", course_details.course_id)
            return result.upserted_id
        else:
            print("No Course Document found for Course Code: ", course_details.course_id)


    def update_video_details(self, video: VideoDetails):
        filter_query = {"video_id": video.video_id}
        video_update = {"name": video.video_name, "summary": video.video_description}
        result = self.video.update_one(filter_query, {"$set": video_update})
        if result.matched_count > 0:
            print("Video Document updated successfully for Video ID: ", video.video_id)
            return True
        else:
            print("No Video Document found for Video Code: ", video.video_id)
            return False

    def get_course_videos(self):
        course_video_result = []
        # TODO: Filter based on visibility
        result = self.course.find({'visibility': 'PUBLIC'})
        for course in result:
            course_video_dict = {
                "courseName": course.get("course_name"),
                "courseCode": course.get("course_code"),
                "visibility": course.get("visibility")
            }
            course_videos = []
            # TODO: Filter based on visibility
            video_result = self.video.find({
                '_id': {'$in': course.get("videos", [])},
                'status': 'COMPLETED',
                'visibility': 'PUBLIC'
            })
            for video in video_result:
                course_videos.append({
                    "videoName": video.get("name", ""),
                    "summary": video.get("video_description", ""),
                    "videoId": video.get("video_id", ""),
                    "thumbnail": video.get("thumbnail", ""),
                    "visibility": video.get("visibility", ""),
                    "status": video.get("status", "")
                })
            course_video_dict["courseVideos"] = course_videos
            course_video_result.append(course_video_dict)

        return course_video_result

    def get_course_videos_manage(self):
        course_video_result = []
        result = self.course.find()
        for course in result:
            course_video_dict = {
                "courseName": course.get("course_name"),
                "courseCode": course.get("course_code"),
                "visibility": course.get("visibility")
            }
            course_videos = []
            video_result = self.video.find({
                '_id': {'$in': course.get("videos", [])}
            })
            for video in video_result:
                course_videos.append({
                    "videoName": video.get("name", ""),
                    "summary": video.get("video_description", ""),
                    "videoId": video.get("video_id", ""),
                    "thumbnail": video.get("thumbnail", ""),
                    "visibility": video.get("visibility", ""),
                    "status": video.get("status", "")
                })
            course_video_dict["courseVideos"] = course_videos
            course_video_result.append(course_video_dict)

        return course_video_result

    def add_course(self, course_code: str, course_name: str, course_description: str):
        try:
            course_id = self.course.find_one({"course_code": course_code})
            if course_id:
                raise Exception("Course Code already exists: ", course_code)

            course_dict = {
                "course_code": course_code,
                "course_name": course_name,
                "course_description": course_description,
                "visibility": "PRIVATE"
            }
            self.course.insert_one(course_dict)
            return
        except Exception as e:
            logger.info("Error when adding course: " + str(e))
            return