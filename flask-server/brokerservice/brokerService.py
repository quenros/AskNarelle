from bson import ObjectId

from brokerservice.repository import BrokerRepository
from brokerservice.status import Status
from loggingConfig import logger
from transcriptservice.TranscriptService import TranscriptService
from videoindexerclient.VideoService import VideoService
from videoindexerclient.model import VideoList


class BrokerService:
    """
    Broker service handles the orchestration of video indexing, transcript processing, and key phrase extraction for course videos.

    Args:
    video_indexer_service (VideoService): Video Service Class. Default: Video Service Class with default arguments.
    transcript_service (TranscriptService): Transcript Service Class. Default: Transcript Service Class with default arguments.
    language_service (LanguageService): Language Service Class. Default: Language Service Class with default arguments.
    broker_db (BrokerRepository): Inject Broker Repository to service. Default: Broker Repository Class with default arguments.
    """
    def __init__(
            self,
            video_indexer_service: VideoService = VideoService(),
            transcript_service: TranscriptService = TranscriptService(),
            broker_db: BrokerRepository = BrokerRepository()
    ):
        self.video_indexer_service = video_indexer_service
        self.transcript_service = transcript_service
        self.broker_db = broker_db

    def start_video_index_process(self, video_list: VideoList):
        """
        Starts the video indexing process by:
        1. Validate Course ID existence. If not valid Course ID, raise an exception. No videos will be processed.
        1. Registering the video in the database.
        2. Sending the video for indexing to Video Indexer.
        3. Fetching insights and associating transcripts.
        4. Extracting key phrases from the transcript.

        Args:
            video_list (VideoList): List of videos to be indexed.
        """
        try:
            course = self.broker_db.check_if_course_exist(video_list.course_code)
            if course == {}:
                raise Exception("Not a valid course Code: ", video_list.course_code)
            video_list = self.register_video(video_list, course["_id"])
            videos = video_list.video
            for video in videos:
                video_object_id = ObjectId(video.video_id)
                print(video_object_id)
                try:
                    print("starting...")
                    video_id, insights = self.video_indexer_service.index_video(video)
                    thumbnail_id = insights["summarizedInsights"]["thumbnailId"]
                    encoded_image = self.video_indexer_service.get_video_thumbnail(video_id, thumbnail_id)
                    self.broker_db.update_video_id_thumbnail(video_object_id, video_id, encoded_image)
                    self.video_indexer_service.get_prompt_content(video_id)
                    result = self.video_indexer_service.database.video_indexer_raw_collection.find_one({'video_indexer_id': video_id})
                    insights = result["insights"]
                    self.transcript_service.map_insights_to_transcript(insights, video_object_id)
                    self.transcript_service.trigger_transcript_cleaning(video_object_id, course, video.video_description)
                    self.transcript_service.update_prompt_with_clean_transcript(video_object_id, video_id)
                    print("Completed Video Indexing Process for ID: ", video_object_id)
                    self.broker_db.change_video_status(video_object_id, Status.COMPLETED)
                except Exception as e:
                    self.broker_db.change_video_status(video_object_id, Status.ERROR)
                    print(e)
        except Exception as e:
            logger.info("An error occurred during start_video_index_process: " + str(e))

    def register_video(self, video_list: VideoList, course_id: ObjectId):
        """
        Registers video in the database.

        Args:
            video_list (VideoList): List of videos to be registered.
            course_id (ObjectId): ObjectId of the course of the video.

        Returns:
            VideoList: Updated video list with database-assigned ObjectId.
        """
        for video in video_list.video:
            video_id = self.broker_db.insert_video_indexing_progress(video, course_id)
            video.video_id = video_id
        logger.info("Video Registration Completed for Course ID: " + str(course_id))
        return video_list

    def get_video(self):
        """
        Retrieve all public videos.

        Returns:
            dict: Public Course-Video information.
        """
        return self.broker_db.get_course_videos()

    def get_video_manage(self):
        """
        Retrieve all videos to be managed.

        Returns:
            dict: Course-Video information.
        """
        return self.broker_db.get_course_videos_manage()

    def add_course(self, course_code, course_name, course_description):
        self.broker_db.add_course(course_code, course_name, course_description)
        return