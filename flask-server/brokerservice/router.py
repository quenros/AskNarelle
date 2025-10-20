from bson import ObjectId
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException
from starlette.responses import JSONResponse

from brokerservice.brokerService import BrokerService
from brokerservice.model import UpdateRequestBody, CourseDetailsRequest, VideoDetailsRequest, CourseDetails
from loggingConfig import logger
from transcriptservice.TranscriptService import TranscriptService

load_dotenv()

router = APIRouter(tags=["broker-service"])

broker_service = BrokerService()

@router.put("/visibility", status_code=200)
def get_videos(body: UpdateRequestBody):
    try:
        output = ""
        if body.type == "VIDEO":
            output = broker_service.broker_db.update_visibility_option_video(body.id, body.newOption)
        elif body.type == "COURSE":
            output = broker_service.broker_db.update_visibility_option_course(body.id, body.newOption)
        if output:
            return JSONResponse(status_code=200, content={"message": "Successfully Updated Visibility"})
        else:
            return JSONResponse(status_code=404, content={"message": "No Records Visibility Updated"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while updating visibility: {str(e)}")

@router.put("/course", status_code=200)
def update_course(body: CourseDetailsRequest):
    try:
        output = broker_service.broker_db.update_course_details(body.course_detail)
        if output:
            return JSONResponse(status_code=200, content={"message": "Successfully Updated Course"})
        else:
            return JSONResponse(status_code=404, content={"message": "No Records Course Updated"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while updating course: {str(e)}")


@router.put("/video", status_code=200)
def update_video(body: VideoDetailsRequest):
    try:
        output = broker_service.broker_db.update_video_details(body.video_detail)
        if output:
            return JSONResponse(status_code=200, content={"message": "Successfully Updated Video"})
        else:
            return JSONResponse(status_code=404, content={"message": "No Records Video Updated"})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error while updating video: {str(e)}")

@router.get("/videos", status_code=200)
def get_videos():
    course_video = broker_service.get_video()
    if course_video:
        return {"message": "Successfully Retrieve", "course_video_mapping": course_video}
    else:
        return {"message": "No Records Found"}

@router.get("/videos/manage", status_code=200)
def get_videos_manage():
    course_video = broker_service.get_video_manage()
    if course_video:
        return {"message": "Successfully Retrieve", "course_video_mapping": course_video}
    else:
        return {"message": "No Records Found"}

@router.post("/course")
def add_course(body: CourseDetails):
    try:
        broker_service.add_course(body.course_id, body.course_name, body.course_description)
        return {"message": "Successfully Added Course"}
    except Exception as e:
        logger.info("Error at /course: " + str(e))
        return JSONResponse(status_code=500, content={"message": "Error adding Course"})
