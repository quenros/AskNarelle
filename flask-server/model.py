from pydantic import BaseModel

class CourseDetails(BaseModel):
    course_id: str
    course_name: str
    course_description: str

class VideoDetails(BaseModel):
    video_id: str
    video_name: str
    video_description: str

class UpdateRequestBody(BaseModel):
    newOption: str
    type: str
    id: str

class CourseDetailsRequest(BaseModel):
    course_detail: CourseDetails

class VideoDetailsRequest(BaseModel):
    video_detail: VideoDetails

    from dataclasses import dataclass

class Consts:
    ApiVersion: str
    ApiEndpoint: str
    AzureResourceManager: str
    AccountName: str
    ResourceGroup: str
    SubscriptionId: str

    def __post_init__(self):
        if self.AccountName is None or self.AccountName == '' \
            or self.ResourceGroup is None or self.ResourceGroup == '' \
            or self.SubscriptionId is None or self.SubscriptionId == '':
            raise ValueError('Please Fill In SubscriptionId, Account Name and Resource Group on the Constant Class!')
