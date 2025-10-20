import base64
import os
import time
from io import BytesIO
from threading import Thread
import requests
from typing import Optional

import schedule

from .Consts import Consts
from .utils import get_arm_access_token, get_account_access_token_async
from loggingConfig import logger


def get_file_name_no_extension(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]


class VideoIndexerClient:
    def __init__(self) -> None:
        self.arm_access_token = ''
        self.vi_access_token = ''
        self.account = None
        self.consts = None

    def authenticate_async(self, consts:Consts) -> None:
        self.consts = consts
        # Get access tokens
        self.arm_access_token = get_arm_access_token(self.consts)
        self.vi_access_token = get_account_access_token_async(self.consts, self.arm_access_token)

    def schedule_authentication(self):
        """
        Schedules authenticate_async to run every 50 minutes.
        """
        schedule.every(30).minutes.do(self.authenticate_async)
        while True:
            schedule.run_pending()
            time.sleep(30)

    def start_authentication_scheduler(self) -> None:
        scheduler_thread = Thread(target=self.schedule_authentication)
        scheduler_thread.start()

    def get_account_async(self) -> None:
        """
        Get information about the account
        """
        if self.account is not None:
            return self.account

        headers = {
            'Authorization': 'Bearer ' + self.arm_access_token,
            'Content-Type': 'application/json'
        }

        url = f'{self.consts.AzureResourceManager}/subscriptions/{self.consts.SubscriptionId}/resourcegroups/' + \
              f'{self.consts.ResourceGroup}/providers/Microsoft.VideoIndexer/accounts/{self.consts.AccountName}' + \
              f'?api-version={self.consts.ApiVersion}'

        response = requests.get(url, headers=headers)

        response.raise_for_status()

        self.account = response.json()
        logger.info(f'[Account Details] Id:{self.account["properties"]["accountId"]}, Location: {self.account["location"]}')

    def file_upload_async(self, media: BytesIO, video_name:Optional[str]=None, excluded_ai:Optional[list[str]]=None,
                          video_description:str='', privacy='private', partition='') -> str:
        """
        Uploads a local file and starts the video index.
        Calls the uploadVideo API (https://api-portal.videoindexer.ai/api-details#api=Operations&operation=Upload-Video)

        :param media: The path to the local file
        :param video_name: The name of the video, if not provided, the file name will be used
        :param excluded_ai: The ExcludeAI list to run
        :param video_description: The description of the video
        :param privacy: The privacy mode of the video
        :param partition: The partition of the video
        :return: Video Id of the video being indexed, otherwise throws exception
        """
        if excluded_ai is None:
            excluded_ai = []


        if video_name is None:
            video_name = "No name"

        self.get_account_async() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/Videos'

        params = {
            'accessToken': self.vi_access_token,
            'name': video_name[:80],
            'description': video_description,
            'privacy': privacy,
            'partition': partition
        }

        if len(excluded_ai) > 0:
            params['excludedAI'] = excluded_ai

        logger.info('Uploading a local file using multipart/form-data post request..')

        response = requests.post(url, params=params, files={'file': media})

        response.raise_for_status()

        if response.status_code != 200:
            logger.info(f'Request failed with status code: {response.status_code}')

        video_id = response.json().get('id')

        return video_id

    def wait_for_index_async(self, video_id:str, language:str='English', timeout_sec:Optional[int]=None) -> None:
        '''
        Calls getVideoIndex API in 10 second intervals until the indexing state is 'processed'
        (https://api-portal.videoindexer.ai/api-details#api=Operations&operation=Get-Video-Index).
        Prints video index when the index is complete, otherwise throws exception.

        :param video_id: The video ID to wait for
        :param language: The language to translate video insights
        :param timeout_sec: The timeout in seconds
        '''
        self.get_account_async() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
            f'Videos/{video_id}/Index'

        params = {
            'accessToken': self.vi_access_token,
            'language': language
        }

        print(f'Checking if video {video_id} has finished indexing...')
        processing = True
        start_time = time.time()
        while processing:
            response = requests.get(url, params=params)

            response.raise_for_status()

            video_result = response.json()
            video_state = video_result.get('state')

            if video_state == 'Processed':
                processing = False
                print(f'The video index has completed. Here is the full JSON of the index for video ID {video_id}: \n{video_result}')
                break
            elif video_state == 'Failed':
                processing = False
                print(f"The video index failed for video ID {video_id}.")
                break

            print(f'The video index state is {video_state}')

            if timeout_sec is not None and time.time() - start_time > timeout_sec:
                print(f'Timeout of {timeout_sec} seconds reached. Exiting...')
                break

            time.sleep(10) # wait 10 seconds before checking again

    def is_video_processed(self, video_id:str) -> bool:
        self.get_account_async() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
                f'Videos/{video_id}/Index'
        params = {
            'accessToken': self.vi_access_token,
        }
        response = requests.get(url, params=params)
        response.raise_for_status()

        video_result = response.json()
        video_state = video_result.get('state')

        return video_state == 'Processed'

    def get_video_async(self, video_id:str) -> dict:
        """
        Gets the video index. Calls the index API
        (https://api-portal.videoindexer.ai/api-details#api=Operations&operation=Search-Videos)
        Prints the video metadata, otherwise throws an exception

        :param video_id: The video ID
        """
        try:
            self.get_account_async() # if account is not initialized, get it
            logger.info(f'Searching videos in account {self.account["properties"]["accountId"]} for video ID {video_id}.')
            url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
                   f'Videos/{video_id}/Index'
            params = {
                'accessToken': self.vi_access_token
            }

            response = requests.get(url, params=params)
            response.raise_for_status()
            search_result = response.json()

            return search_result
        except Exception as e:
            logger.info("get_video_async", e)

    def generate_prompt_content_async(self, video_id:str) -> None:
        """
        Calls the promptContent API
        Initiate generation of new prompt content for the video.
        If the video already has prompt content, it will be replaced with the new one.

        :param video_id: The video ID
        """
        self.get_account_async() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
              f'Videos/{video_id}/PromptContent'

        headers = {
            "Content-Type": "application/json"
            }

        params = {
            'accessToken': self.vi_access_token
        }

        response = requests.post(url, headers=headers, params=params)

        response.raise_for_status()
        print(f"Prompt content generation for {video_id=} started...")

    def get_prompt_content_async(self, video_id:str, raise_on_not_found:bool=True) -> Optional[dict]:
        """
        Calls the promptContent API
        Get the prompt content for the video.
        Raises an exception or returns None if the prompt content is not found according to the `raise_on_not_found`.

        :param video_id: The video ID
        :param raise_on_not_found: If True, raises an exception if the prompt content is not found.
        :return: The prompt content for the video, otherwise None
        """
        self.get_account_async() # if account is not initialized, get it

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
              f'Videos/{video_id}/PromptContent'

        headers = {
            "Content-Type": "application/json"
            }

        params = {
            'accessToken': self.vi_access_token
        }

        response = requests.get(url, params=params)
        if not raise_on_not_found and response.status_code == 404:
            return None

        response.raise_for_status()

        return response.json()

    def get_prompt_content(self, video_id:str, timeout_sec:Optional[int]=None,
                           check_alreay_exists=True) -> Optional[dict]:
        """
        Gets the prompt content for the video, waits until the prompt content is ready.
        If the prompt content is not ready within the timeout, it will return None.

        :param video_id: The video ID
        :param timeout_sec: The timeout in seconds
        :param check_alreay_exists: If True, checks if the prompt content already exists
        :return: The prompt content for the video, otherwise None
        """

        if check_alreay_exists:
            prompt_content = self.get_prompt_content_async(video_id, raise_on_not_found=False)
            if prompt_content is not None:
                print(f'Prompt content already exists for video ID {video_id}.')
                return prompt_content

        self.generate_prompt_content_async(video_id)

        start_time = time.time()
        prompt_content = None
        while prompt_content is None:
            prompt_content = self.get_prompt_content_async(video_id, raise_on_not_found=False)

            if timeout_sec is not None and time.time() - start_time > timeout_sec:
                print(f'Timeout of {timeout_sec} seconds reached. Exiting...')
                break

            print('Prompt content is not ready yet. Waiting 5 seconds before checking again...')
            time.sleep(10)

        return prompt_content

    def get_insights_widgets_url_async(self, video_id:str, widget_type:list, allow_edit:bool=False) -> str:
        '''
        Calls the getVideoInsightsWidget API
        (https://api-portal.videoindexer.ai/api-details#api=Operations&operation=Get-Video-Insights-Widget)
        It first generates a new access token for the video scope.
        Prints the VideoInsightsWidget URL, otherwise throws exception.

        :param video_id: The video ID
        :param widget_type: The widget type
        :param allow_edit: Allow editing the video insights
        '''
        self.get_account_async() # if account is not initialized, get it

        # generate a new access token for the video scope
        video_scope_access_token = get_account_access_token_async(self.consts, self.arm_access_token,
                                                                  permission_type='Contributor', scope='Video',
                                                                  video_id=video_id)

        print(f'Getting the insights widget URL for video {video_id}')

        params = {
            'widgetType': widget_type,
            'allowEdit': str(allow_edit).lower(),
            'accessToken': video_scope_access_token
        }

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
              f'Videos/{video_id}/InsightsWidget'

        response = requests.get(url, params=params)

        response.raise_for_status()

        insights_widget_url = response.url
        print(f'Got the insights widget URL: {insights_widget_url}')
        return insights_widget_url

    def get_player_widget_url_async(self, video_id:str) -> str:
        """
        Calls the getVideoPlayerWidget API
        (https://api-portal.videoindexer.ai/api-details#api=Operations&operation=Get-Video-Player-Widget)
        It first generates a new access token for the video scope.
        Prints the VideoPlayerWidget URL, otherwise throws exception

        :param video_id: The video ID
        """
        self.get_account_async()

        # generate a new access token for the video scope
        video_scope_access_token = get_account_access_token_async(self.consts, self.arm_access_token,
                                                                  permission_type='Contributor', scope='Video',
                                                                  video_id=video_id)

        print(f'Getting the player widget URL for video {video_id}')

        params = {
            'accessToken': video_scope_access_token
        }

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
              f'Videos/{video_id}/PlayerWidget'

        response = requests.get(url, params=params)

        response.raise_for_status()

        url = response.url
        print(f'Got the player widget URL: {url}')
        return url

    def get_video_thumbnail(self, video_id: str, thumbnail_id: str):
        self.get_account_async()

        # generate a new access token for the video scope
        video_scope_access_token = get_account_access_token_async(self.consts, self.arm_access_token,
                                                                  permission_type='Contributor', scope='Video',
                                                                  video_id=video_id)

        print(f'Getting thumbnail for video {video_id}')

        params = {
            'accessToken': video_scope_access_token
        }

        url = f'{self.consts.ApiEndpoint}/{self.account["location"]}/Accounts/{self.account["properties"]["accountId"]}/' + \
              f'Videos/{video_id}/Thumbnails/{thumbnail_id}'

        response = requests.get(url, params=params)

        content_type = response.headers.get('Content-Type', '')
        encoded_image = ""

        if 'image' in content_type:
            encoded_image = base64.b64encode(response.content).decode('utf-8')

        response.raise_for_status()

        return encoded_image

