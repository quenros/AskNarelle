from flask import Flask, request, jsonify
import os
from flask_cors import CORS
from mongo_helper import  create_document, delete_all_course_documents, delete_document,  get_documents, update_movement_document, get_chatlogs, upload_course, list_courses, upload_domain, get_domain_files, delete_domain_docs, get_course_files_count, get_domain_files_count, get_users_count, get_queries_count, get_queries_by_month, get_queries_by_course, get_user_sentiments, get_user_emotions, check_if_rec_exists, get_course_users,  detele_course_user, add_activity, view_activities
from blob_storage_helper import createContainer, delete_blob_storage_container, upload_to_azure_blob_storage, delete_from_azure_blob_storage,delete_domain_virtual_folder, generate_sas_token
from ai_search_helper import storeDocuments, moveToVectorStoreFunction,createIndexFucntion, delete_index_function, delete_embeddings_function
from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from datetime import datetime
# import pytz 
from pytz import timezone,utc
import requests
from course_share_helper import get_access_token

load_dotenv()

app = Flask(__name__)
CORS(app)


blob_service_client = BlobServiceClient.from_connection_string(os.environ.get('AZURE_CONN_STRING'))
graph_url = 'https://graph.microsoft.com/v1.0/'

@app.route("/vectorstore", methods=['PUT'])
def storeInVectorStore():
    print("Entered Function")
    data = request.json
    containername = data.get('containername')
    chunksize= int(data.get('chunksize'))
    overlap = int(data.get('overlap'))


    store_status = storeDocuments(containername, chunksize, overlap)
    if(store_status == "True"):
        return jsonify({"message": "Data loaded into vectorstore successfully"}), 201
    else:
        return jsonify({"message": store_status}), 500

   
@app.route("/movetovectorstore", methods=['PUT'])
def moveToVectorStore():
    data = request.json
    containername = data.get('containername')
    domainname = data.get('domainname')
    versionid = data.get('versionid')
    chunksize= int(data.get('chunksize'))
    overlap = int(data.get('overlap'))
    filename = data.get('filename')


    movement_status = moveToVectorStoreFunction(containername, domainname, versionid, chunksize, overlap, filename)
    print(movement_status)
    if movement_status:  
        return jsonify({"message": "Data moved into into vectorstore successfully"}), 201
    else:
        return jsonify({"message": "Data failed to move into store"}), 500


@app.route("/createindex", methods=['PUT'])
def createIndex():
    data = request.json
    collection_name = data.get('collectionName')

    create_index_status =  createIndexFucntion(collection_name)
    if create_index_status:  
        return jsonify({"message": "Index created successfully"}), 201
    else:
        return jsonify({"message": "Failed to create index"}), 500

    
@app.route('/api/createcollection', methods=['PUT'])
def create_course():
    data = request.json
    collection_name = data.get('collectionName')
    username = data.get('username')

    collection_name = collection_name.lower().replace(' ', '-')
    if not collection_name:
        return jsonify({"error": "Collection name is required"}), 400
    try:
        create_success_container = createContainer(collection_name)
        if create_success_container:
                uploaded_course = upload_course(collection_name, username)
                if uploaded_course:
                    return jsonify({"message": "Container and course created successfully!"}), 201
                else:
                    return jsonify({"message": "Failed to upload course"}), 500
        else:
            return jsonify({'error': 'Container already exsists'}), 500
    except Exception as error:
        return jsonify({'error': 'Internal server error'}), 500
    
@app.route('/api/createdomain', methods=['PUT'])
def create_domain():
    data=request.json
    domain_name = data.get('domainName')
    collection_name = data.get('courseName')
    username = data.get('user')
    action = data.get('action')

    activities = []

    domain_name = domain_name.lower().replace(' ', '-')
    try:
        upload_domain_success, message = upload_domain(domain_name, collection_name)
        if upload_domain_success:
            timestamp_dt = utc.localize(datetime.utcnow())
            local_tz = timezone('Asia/Singapore')
            local_timestamp_dt = timestamp_dt.astimezone(local_tz)

            date_str = local_timestamp_dt.date().isoformat()
            time_str = local_timestamp_dt.strftime('%H:%M:%S')

            activities.append({
                    "uername": username,
                    "course_name": collection_name,
                    "domain": domain_name,
                    "file": "null",
                    "action": action,
                    "date_str": date_str,
                    "time_str": time_str
                })

            add_activity_status = add_activity(activities)
            if add_activity_status:
               return jsonify({"message": "Domain created successfully"}), 201
            else:
                return jsonify({"message": "Activity was not added successfully"}), 500
            
        else:
            return jsonify({"message": message}), 400
        
    except Exception as error:
        return jsonify({'error': 'Internal server error'}), 500 


@app.route('/api/collections/<username>', methods=['GET'])
def get_containers(username):
    containers =  list_courses(username)
    return jsonify(containers), 201

@app.route('/api/collections/<username>/<collection_name>/domains', methods=['GET'])
def get_domains(username,collection_name):
    username = username.lower()
    domain_status = get_domain_files(username,collection_name)

    if domain_status == "403":
       return jsonify({"message": "User is not authorised to access this page"}), 403
    elif domain_status == "404":
       return jsonify({"message": "This page is not available"}), 404
    elif domain_status == "Flase":
        return jsonify({"message": "Error fetch course domains"}), 500
    else:
        return jsonify(domain_status), 201

@app.route('/api/collections/<username>/<collection_name>/<domain_name>', methods=['GET'])
def get_files(username,collection_name, domain_name):
    documents_status = get_documents(username,collection_name, domain_name)
    # print(documents_status)

    if documents_status == "403":
       return jsonify({"message": "User is not authorised to access this page"}), 403
    elif documents_status == "404":
       return jsonify({"message": "This page is not available"}), 404
    elif documents_status == "Flase":
        return jsonify({"message": "Error fetch course files"}), 500
    else:
        return jsonify(documents_status), 201


@app.route('/api/<collection_name>/<domain_name>/<username>/createblob', methods=['PUT'])
def upload_blob(collection_name, domain_name, username):
    files = request.files.getlist('files')
    container_name = collection_name.lower().replace(' ', '-')
    allowed_extensions = {'.pdf', '.docx', '.txt', '.pptx'}
   

    for file in files:
        if(os.path.splitext(file.filename)[1].lower() not in allowed_extensions):
            return jsonify({'error': 'Invalid files'}), 400
    try:
        # now_utc = datetime.now(pytz.utc)
       
        upload_success = upload_to_azure_blob_storage(container_name, files, domain_name)
        if upload_success:
            return jsonify({'message': 'Files uploaded succesfully to Azure Blob Storage'}), 201

        else:
            return jsonify({'error': 'Failed to upload files to Azure Blob Storage'}), 500
    except Exception as error:
            print(f"Error processing files upload: {error}")
            return jsonify({'error': 'Internal server error'}), 500
    
@app.route('/api/<collection_name>/<domain_name>/<username>/createdocument', methods=['PUT'])
def upload_document(collection_name, domain_name, username):
     files = request.files.getlist('files')
     container_name = collection_name.lower().replace(' ', '-')
     files_with_links = []
     activities = []
     container_client = blob_service_client.get_container_client(collection_name)
     for file in files:
        blob_client_direct = container_client.get_blob_client(f"{domain_name}/{file.filename}")
        blob_version = blob_client_direct.get_blob_properties().version_id
        main_part, fractional_part = blob_version[:-1].split('.')
        fractional_part = fractional_part[:6] 
        adjusted_timestamp_str = f"{main_part}.{fractional_part}Z"
        timestamp_dt = datetime.strptime(adjusted_timestamp_str, '%Y-%m-%dT%H:%M:%S.%fZ')
        timestamp_dt = utc.localize(timestamp_dt)

        local_tz = timezone('Asia/Singapore')
        local_timestamp_dt = timestamp_dt.astimezone(local_tz)
    
        date_str = local_timestamp_dt.date().isoformat()
        time_str = local_timestamp_dt.strftime('%H:%M:%S')

        print(date_str)
        print(time_str)

        print(f"this is blob version: {blob_version}")
        sas_token = generate_sas_token(container_name, f'{domain_name}/{file.filename}')
        blob_url = f"https://{blob_service_client.account_name}.blob.core.windows.net/{container_name}/{f'{domain_name}/{file.filename}'}?{sas_token}"
        files_with_links.append({
            "course_name" : container_name,
            "domain": domain_name,
            "name": file.filename,
            "url": blob_url,
            "blob_name": f'{domain_name}/{file.filename}',
            "version_id": blob_version,
            "date_str": date_str,
            "time_str": time_str,
            "in_vector_store": 'yes',
            "is_root_blob": 'yes',
        
        })
        activities.append({
            "uername": username,
            "course_name": collection_name,
            "domain": domain_name,
            "file": file.filename,
            "action": "Uploaded File",
            "date_str": date_str,
            "time_str": time_str
        })
     create_document_success = create_document(files_with_links)
     if create_document_success:
        add_activity_status = add_activity(activities)
        if add_activity_status:
            return jsonify({"message": "Documents created successfully!"}), 201
        else:
            return jsonify({'error': 'Failed to upload activity status'}), 500
     else:
        return jsonify({'error': 'Failed to create documents'}), 500
        

@app.route('/api/deletecourse', methods=['DELETE'])
def delete_course():
    data = request.json
    collection_name = data.get('collectionName')
    collection_name = collection_name.lower().replace(' ', '-')
    if not collection_name:
        return jsonify({"error": "Collection name is required"}), 400
    try:
        delete_index = delete_index_function(collection_name)
        if delete_index:
            delete_success_container = delete_blob_storage_container(collection_name)
            if delete_success_container:
                delete_all_course_docs = delete_all_course_documents(collection_name)
                if(delete_all_course_docs):
                    return jsonify({"message": "Container deleted successfully!"}), 201
                else:
                    return jsonify({"message: Failed to delete the documents"}), 500
            else:
                return jsonify({'error': 'Failed to delete contaier'}), 500
        else: 
            return jsonify({'error': 'Failed to delete index'}), 500
        
    except Exception as error:
        return jsonify({'error': 'Internal server error'}), 500
    
    
    
@app.route('/api/deletedomain', methods=['DELETE'])
def delete_domain():
    data = request.json
    course_name = data.get('collectionName')
    domain_name = data.get('domainName')
    username = data.get('username')
    activities = []
    try:
        domain_docs = get_documents(username, course_name, domain_name)
        for doc in domain_docs:
            deletion_status = delete_embeddings_function(doc['name'], course_name)
            if not deletion_status:
                return jsonify({"message: Failed to delete embeddings"}), 500
                    
        delete_success_domain_folder = delete_domain_virtual_folder(course_name, domain_name)
        if delete_success_domain_folder:
            delete_success_domain_docs = delete_domain_docs(course_name, domain_name)
            if delete_success_domain_docs:
                timestamp_dt = utc.localize(datetime.utcnow())
                local_tz = timezone('Asia/Singapore')
                local_timestamp_dt = timestamp_dt.astimezone(local_tz)

                date_str = local_timestamp_dt.date().isoformat()
                time_str = local_timestamp_dt.strftime('%H:%M:%S')


                activities.append({
                                "uername": username,
                                "course_name": course_name,
                                "domain": domain_name,
                                "file": "null",
                                "action": "Deleted Domain",
                                "date_str": date_str,
                                "time_str": time_str
                            })

                add_activity_status = add_activity(activities)

                if add_activity_status:
                   return jsonify({"message": "Domain deleted successfully!"}), 201
                else:
                    return jsonify({"message: Failed to add activity status"}), 500

            else:
                    return jsonify({"message: Failed to delete the domain documents"}), 500
        else:
            return jsonify({'error': 'Failed to delete contaier'}), 500
    except Exception as error:
        return jsonify({'error': 'Internal server error'}), 500


@app.route('/api/<collection_name>/<domain_name>/deletedocument', methods=['DELETE'])
def delete_file(collection_name, domain_name):
    data = request.json
    file_name = data.get('fileName')
    file_id = data.get('_id')
    version_id = data.get('versionId')
    is_root_blob = data.get('isRootBlob')
    container_name = collection_name.lower().replace(' ', '-')
    username = data.get('username')
    action = data.get('action')

    activities = []

    try:
        delete_success = delete_from_azure_blob_storage(container_name, file_name, domain_name, version_id, is_root_blob)
        if delete_success:
            delete_document_success =  delete_document(collection_name, file_id, is_root_blob, file_name)
            if delete_document_success:
                timestamp_dt = utc.localize(datetime.utcnow())
                local_tz = timezone('Asia/Singapore')
                local_timestamp_dt = timestamp_dt.astimezone(local_tz)

                date_str = local_timestamp_dt.date().isoformat()
                time_str = local_timestamp_dt.strftime('%H:%M:%S')

                activities.append({
                                "uername": username,
                                "course_name": container_name,
                                "domain": domain_name,
                                "file": file_name,
                                "action": action,
                                "date_str": date_str,
                                "time_str": time_str
                            })

                add_activity_status = add_activity(activities)
                if add_activity_status: 
                   return jsonify({"message": "Document deleted successfully!"}), 201
                else:
                    return jsonify({'error': 'Failed to add activity'}), 500

            else:
                return jsonify({'error': 'Failed to delete document'}), 500
        else:
            return jsonify({'error': 'Failed to upload file to Azure Blob Storage'}), 500
    except Exception as error:
            print(f"Error processing file upload: {error}")
            return jsonify({'error': 'Internal server error'}), 500
    
@app.route("/api/<collection_name>/deleteembeddings", methods=['DELETE'])
def DeleteEmbeddings(collection_name):
    data = request.json
    blobName = data.get('fileName')

    embeddings_delete_status = delete_embeddings_function(blobName, collection_name)
    
    if embeddings_delete_status:  
        return jsonify({"message": "Embeddings deleted successfully"}), 201
    else:
        return jsonify({"message": "Failed to delete embeddings"}), 500
    
    
@app.route('/updatemovement', methods=['PUT'])
def update_movement():
    data = request.json
    collection_name = data.get('collectionName')
    domain_name = data.get('domainName')
    file_name = data.get('fileName')
    version_id = data.get('versionId')
    username = data.get('username')

    activities = []

    try:
        create_document_success = update_movement_document(collection_name, file_name, version_id)
        if create_document_success:
            timestamp_dt = utc.localize(datetime.utcnow())
            local_tz = timezone('Asia/Singapore')
            local_timestamp_dt = timestamp_dt.astimezone(local_tz)

            date_str = local_timestamp_dt.date().isoformat()
            time_str = local_timestamp_dt.strftime('%H:%M:%S')

            activities.append({
                            "uername": username,
                            "course_name": collection_name,
                            "domain": domain_name,
                            "file": file_name,
                            "action": "Moved to vector store",
                            "date_str": date_str,
                            "time_str": time_str
                        })

            add_activity_status = add_activity(activities)

            if add_activity_status:
               return jsonify({"message": "Documents created successfully!"}), 201
            else:
                return jsonify({'error': 'Failed to add activity'}), 500

        else:
            return jsonify({'error': 'Failed to create documents'}), 500
        
    except Exception as error:
            print(f"Error processing files upload: {error}")
            return jsonify({'error': 'Internal server error'}), 500

@app.route('/get-chats', methods=['GET'])
def get_chats():
    chats = get_chatlogs()
    # print(chats)
    return jsonify(chats), 201


@app.route('/manageaccess/<course_name>', methods=['GET'])
def getCourseUsers(course_name):
    usersList = get_course_users(course_name)
    if(usersList is False):
        return jsonify({'message': 'Error fetching users of this course'}), 500
    else:
        return jsonify(usersList), 201


@app.route('/manageaccess/deleteUser', methods=['DELETE'])
def deleteCourseUsers():
    data = request.json
    course_name = data.get('collectionName')
    user = data.get('username')

    deletionStatus = detele_course_user(course_name, user)
    if(deletionStatus):
        return jsonify({'message': 'Successfully revoked access to the user'}), 201
    else:
        return jsonify({'message': 'Coul not revoke access to the user'}), 500


@app.route('/api/<course_name>/totalFiles', methods = ['GET'])
def getTotalCourseFiles(course_name):
    courseFilesCount = get_course_files_count(course_name)
    if courseFilesCount == "False":
       return jsonify({'message': 'Error fetching files count'}), 500
    else:
        return jsonify(courseFilesCount), 201
    
@app.route('/api/<course_name>/<domain_name>/totalFiles', methods = ['GET'])
def getTotalDomainFiles(course_name, domain_name):
    domainFilesCount = get_domain_files_count(course_name, domain_name)
    if domainFilesCount == "False":
       return jsonify({'message': 'Error fetching files count'}), 500
    else:
        return jsonify(domainFilesCount), 201
    
@app.route('/chats/totalUsers/<username>', methods = ['GET'])
def getTotalUsers(username):
    usersCount = get_users_count(username)
    if usersCount == "False":
       return jsonify({'message': 'Error fetching files count'}), 500
    else:
        return jsonify(usersCount), 201
    
@app.route('/chats/totalQueries/<username>', methods = ['GET'])
def getTotalQueries(username):
    queriesCount = get_queries_count(username)
    if queriesCount == "False":
       return jsonify({'message': 'Error fetching files count'}), 500
    else:
        return jsonify(queriesCount), 201

@app.route('/chats/queriesByMonth/<username>', methods=['GET'])
def getQueriesByMonth(username):
    queries_by_month = get_queries_by_month(username)
    if queries_by_month == "False":
        return jsonify({'message': 'Error fetching files count'}), 500
    else:
        return queries_by_month, 201
    
@app.route('/chats/queriesByCourse/<username>', methods=['GET'])
def getQueriesByCourse(username):
    queries_by_course = get_queries_by_course(username)
    if queries_by_course == "False":
        return jsonify({'message': 'Error fetching query count by course'}), 500
    else:
        return queries_by_course, 201
    
@app.route('/chats/userSentiments/<username>', methods=['GET'])
def getUserSentiments(username):
    user_sentiments = get_user_sentiments(username)
    if user_sentiments == "False":
        return jsonify({'message': 'Error fetching user sentiments'}), 500
    else:
        return user_sentiments, 201
    
@app.route('/chats/userEmotions/<username>', methods=['GET'])
def getUserEmotions(username):
    user_emotions = get_user_emotions(username)
    if user_emotions == "False":
        return jsonify({'message': 'Error fetching user emotions'}), 500
    else:
        return user_emotions, 201
    
@app.route('/invite', methods=['POST'])
def invite_user():
    data = request.get_json()
    email = data.get('email')
    courseName = data.get('course')

    if not email:
        return jsonify({'error': 'Email is required'}), 400
    
    # if not email.endswith("ntu.edu.sg"):
    #     return jsonify({'error': 'Invalid email domain. Only NTU email is allowed.'}), 400


    token = get_access_token()
    
    if not token:
        return jsonify({'error': 'Unable to acquire access token'}), 500

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    if(check_if_rec_exists(email, courseName)):
        return jsonify({'error': 'User already has access to this folder'}), 500
    
    user_check_url = graph_url + f"users?$filter=mail eq '{email}' or userPrincipalName eq '{email}'"
    user_response = requests.get(user_check_url, headers=headers)
    
    if user_response.status_code == 200:  
        user_data = user_response.json()

        # Check if the user exists
        if len(user_data.get('value', [])) > 0:
            upload_status = upload_course(courseName, email)
            if(upload_status):
                return jsonify({'message': 'User added to access this course'}), 201
            else:
                return jsonify({'error': 'Error in adding user'}), 500

          
        else:
            invite_url = graph_url + 'invitations'
            invite_body = {
                "invitedUserEmailAddress": email,
                "inviteRedirectUrl": "https://asknarelle-frontend.azurewebsites.net",
                "sendInvitationMessage": True
            }
            
            invite_response = requests.post(invite_url, headers=headers, json=invite_body)
            print(invite_response.text)
            print(invite_response.status_code)
            if invite_response.status_code == 201:
                upload_course(courseName, email)
                return jsonify({'message': 'Invitation sent successfully!'}), 201
            else:
                print(invite_response.json())
                return jsonify({'error': invite_response.json()}), invite_response.status_code
    else:
        print(user_response.json())
        return jsonify({'error': user_response.json()}), user_response.status_code
    
@app.route('/activities/<username>/viewactivities', methods=['GET'])  
def get_activities(username):
    print(username)
    activities = view_activities(username)
    if activities is not False:
        return jsonify(activities), 201
    else:
        return jsonify({"message": "Error fetching activities"}), 500


if __name__ == "__main__":
    app.run(debug=True)