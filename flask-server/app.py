from flask import Flask, request, jsonify
import threading
from bson import ObjectId
from datetime import datetime
import os
from flask_cors import CORS
from mongo_helper import (
    create_document,
    delete_all_course_documents,
    delete_document,
    get_documents,
    update_movement_document,
    get_chatlogs,
    upload_course,
    list_courses,
    upload_domain,
    get_domain_files,
    delete_domain_docs,
    get_course_files_count,
    get_domain_files_count,
    get_users_count,
    get_queries_count,
    get_queries_by_month,
    get_queries_by_course,
    get_user_sentiments,
    get_user_emotions,
    check_if_rec_exists,
    get_course_users,
    delete_course_user,
    add_activity,
    view_activities,
)
from blob_storage_helper import (
    createContainer,
    delete_blob_storage_container,
    upload_to_azure_blob_storage,
    delete_from_azure_blob_storage,
    delete_domain_virtual_folder,
    generate_sas_token,
    attach_sas_urls_to_documents,
    build_blob_sas_url,
    get_blob_text,
)
from ai_search_helper import (
    storeDocuments,
    moveToVectorStoreFunction,
    createIndexFunction,
    delete_index_function,
    delete_embeddings_function,
    search_documents
)
# from ai_search_helper_local import (storeDocuments, moveToVectorStoreFunction, createIndexFunction, delete_index_function, delete_embeddings_function)
from video_indexer_helper import (
    vi_add_course,
    check_if_course_exist,
    insert_video_indexing_progress,
    index_video_and_update_metadata,
    get_video_document_by_id,
    delete_video_entry_from_db,
    get_course_videos_manage,
    get_all_video_ids_for_course,
    VideoIndexerClient,
    VideoDetails,
)

from chat_helper import chat_client, ChatRequestBody

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient
from datetime import datetime
from pytz import timezone, utc
import requests
from course_share_helper import get_access_token

from model import VideoDetails 

load_dotenv()

app = Flask(__name__)
CORS(app)

blob_service_client = BlobServiceClient.from_connection_string(
    os.environ.get("AZURE_CONN_STRING")
)
graph_url = "https://graph.microsoft.com/v1.0/"

@app.route("/vectorstore", methods=["PUT"])
def storeInVectorStore():
    data = request.json
    containername = data.get("containername")
    chunksize = int(data.get("chunksize"))
    overlap = int(data.get("overlap"))

    result = storeDocuments(containername, chunksize, overlap)

    if result == "True":
        return jsonify({"message": "Data loaded into vectorstore successfully"}), 201
    else:
        return jsonify({"error": str(result)}), 500


TEXT_EXTS = {".pdf", ".docx", ".pptx", ".txt"}


@app.route("/movetovectorstore", methods=["PUT"])
def moveToVectorStore():
    data = request.json
    containername = data.get("containername")
    domainname = data.get("domainname")
    chunksize = int(data.get("chunksize"))
    overlap = int(data.get("overlap"))
    filename = data.get("filename") or ""

    # Block non-text files from going to vector store (videos, etc.)
    ext = os.path.splitext(filename)[1].lower()
    if ext not in TEXT_EXTS:
        return (
            jsonify(
                {
                    "message": f"File type '{ext}' cannot be moved into the vector store."
                }
            ),
            400,
        )

    movement_status = moveToVectorStoreFunction(
        containername, domainname, chunksize, overlap, filename
    )
    print(movement_status)
    if movement_status:
        return (
            jsonify({"message": "Data moved into into vectorstore successfully"}),
            201,
        )
    else:
        return jsonify({"message": "Data failed to move into store"}), 500


@app.route("/createindex", methods=["PUT"])
def createIndex():
    data = request.json
    collection_name = data.get("collectionName")

    create_index_status = createIndexFunction(collection_name)
    if create_index_status:
        return jsonify({"message": "Index created successfully"}), 201
    else:
        return jsonify({"message": "Failed to create index"}), 500


@app.route("/api/createcollection", methods=["PUT"])
def create_course():
    data = request.json
    collection_name = data.get("collectionName")
    username = data.get("username")

    collection_name = collection_name.lower().replace(" ", "-")
    if not collection_name:
        return jsonify({"error": "Collection name is required"}), 400
    try:
        create_success_container = createContainer(collection_name)
        if create_success_container:
            uploaded_course = upload_course(collection_name, username)
            if uploaded_course:
                return (
                    jsonify(
                        {"message": "Container and course created successfully!"}
                    ),
                    201,
                )
            else:
                return jsonify({"message": "Failed to upload course"}), 500
        else:
            return jsonify({"error": "Container already exsists"}), 500
    except Exception as error:
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/createdomain", methods=["PUT"])
def create_domain():
    data = request.json
    domain_name = data.get("domainName")
    collection_name = data.get("courseName")
    username = data.get("user")
    action = data.get("action")

    activities = []

    domain_name = domain_name.lower().replace(" ", "-")
    try:
        upload_domain_success, message = upload_domain(domain_name, collection_name)
        if upload_domain_success:
            timestamp_dt = utc.localize(datetime.utcnow())
            local_tz = timezone("Asia/Singapore")
            local_timestamp_dt = timestamp_dt.astimezone(local_tz)

            date_str = local_timestamp_dt.date().isoformat()
            time_str = local_timestamp_dt.strftime("%H:%M:%S")

            activities.append(
                {
                    "uername": username,
                    "course_name": collection_name,
                    "domain": domain_name,
                    "file": "null",
                    "action": action,
                    "date_str": date_str,
                    "time_str": time_str,
                }
            )

            add_activity_status = add_activity(activities)
            if add_activity_status:
                return jsonify({"message": "Domain created successfully"}), 201
            else:
                return jsonify(
                    {"message": "Activity was not added successfully"}), 500

        else:
            return jsonify({"message": message}), 400

    except Exception as error:
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/collections/<username>", methods=["GET"])
def get_containers(username):
    containers = list_courses(username)
    return jsonify(containers), 201


@app.route(
    "/api/collections/<username>/<collection_name>/domains", methods=["GET"]
)
def get_domains(username, collection_name):
    username = username.lower()
    domain_status = get_domain_files(username, collection_name)

    if domain_status == "403":
        return (
            jsonify({"message": "User is not authorised to access this page"}),
            403,
        )
    elif domain_status == "404":
        return jsonify({"message": "This page is not available"}), 404
    elif domain_status == "Flase":
        return jsonify({"message": "Error fetch course domains"}), 500
    else:
        return jsonify(domain_status), 201


@app.route(
    "/api/collections/<username>/<collection_name>/<domain_name>", methods=["GET"]
)
def get_files(username, collection_name, domain_name):
    documents_status = get_documents(username, collection_name, domain_name)

    # if we got a real list of docs back, attach fresh SAS URLs and return
    if isinstance(documents_status, list):
        docs_with_sas = attach_sas_urls_to_documents(documents_status)
        return jsonify(docs_with_sas), 200  

    # Handle error/status codes coming back as strings
    if documents_status == "403":
        return (
            jsonify({"message": "User is not authorised to access this page"}),
            403,
        )
    elif documents_status == "404":
        return jsonify({"message": "This page is not available"}), 404
    elif documents_status == "False":  # <- fixed typo
        return jsonify({"message": "Error fetching course files"}), 500
    else:
        # Unexpected case
        return jsonify({"message": "Unknown error"}), 500
    

@app.route("/api/preview/<collection_name>/<domain_name>", methods=["GET"])
def preview_file(collection_name, domain_name):
    # Treat CSV, JSON, MD as text so we can read their content directly
    TEXT_EXTS = {".txt", ".csv", ".md", ".json"} 
    VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".webm", ".avi"}
    PDF_EXTS = {".pdf"}
    # for office docs
    OFFICE_EXTS = {".docx", ".doc", ".pptx", ".ppt", ".xlsx"} 

    file_name = request.args.get("name")
    if not file_name:
        return jsonify({"error": "name query parameter is required"}), 400

    container_name = collection_name.lower().replace(" ", "-")
    blob_path = f"{domain_name}/{file_name}"
    ext = os.path.splitext(file_name)[1].lower()

    try:
        # .txt, .csv 
        if ext in TEXT_EXTS:
            text = get_blob_text(container_name, blob_path)
            return jsonify({
                "name": file_name,
                "kind": "text",
                "content": text,
            }), 200

        blob_url = build_blob_sas_url(container_name, blob_path)

        kind = "other"
        if ext in VIDEO_EXTS:
            kind = "video"
        elif ext in PDF_EXTS:
            kind = "pdf"
        elif ext in OFFICE_EXTS:
            kind = "office" 

        return jsonify({
            "name": file_name,
            "kind": kind,
            "url": blob_url,
        }), 200

    except Exception as e:
        print("preview_file error:", e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/<collection_name>/<domain_name>/<username>/createblob", methods=["PUT"])
def upload_blob(collection_name, domain_name, username):
    files = request.files.getlist("files")
    container_name = collection_name.lower().replace(" ", "-")
    allowed_doc_exts = {".pdf", ".docx", ".txt", ".pptx", ".csv", ".xlsx"}
    allowed_video_exts = {".mp4", ".mov", ".avi", ".mkv"}
    allowed_extensions = allowed_doc_exts | allowed_video_exts

    for file in files:
        if os.path.splitext(file.filename)[1].lower() not in allowed_extensions:
            return jsonify({"error": "Invalid files"}), 400
    try:
        upload_success = upload_to_azure_blob_storage(
            container_name, files, domain_name
        )
        if upload_success:
            return (
                jsonify(
                    {"message": "Files uploaded succesfully to Azure Blob Storage"}
                ),
                201,
            )

        else:
            return jsonify(
                {"error": "Failed to upload files to Azure Blob Storage"}
            ), 500
    except Exception as error:
        print(f"Error processing files upload: {error}")
        return jsonify({"error": "Internal server error"}), 500


@app.route(
    "/api/<collection_name>/<domain_name>/<username>/createdocument", methods=["PUT"]
)
def upload_document(collection_name, domain_name, username):
    files = request.files.getlist("files")
    container_name = collection_name.lower().replace(" ", "-")
    files_with_links, activities = [], []

    # only text-like files are vectorized
    text_exts = {".pdf", ".docx", ".pptx", ".txt"}

    try:
        container_client = blob_service_client.get_container_client(container_name)

        for file in files:
            blob_path = f"{domain_name}/{file.filename}"
            blob_client_direct = container_client.get_blob_client(blob_path)

            # Properties
            props = blob_client_direct.get_blob_properties()
            version_id = getattr(props, "version_id", None)  # may be None
            last_modified_utc = props.last_modified  # tz-aware datetime in UTC

            # Fallback version_id when blob versioning is disabled
            if not version_id:
                version_id = f"{blob_path}:{int(last_modified_utc.timestamp())}"

            # Derive local timestamp (Asia/Singapore)
            local_tz = timezone("Asia/Singapore")

            # Try to parse a time from version_id when available (Azure often returns ISO-like with 7-digit micros)
            date_str = time_str = None
            if isinstance(version_id, str) and "T" in version_id:
                try:
                    raw = version_id
                    if raw.endswith("Z"):
                        raw = raw[:-1]
                        if "." in raw:
                            main, frac = raw.split(".", 1)
                            frac = "".join(ch for ch in frac if ch.isdigit())[:6]
                            raw = f"{main}.{frac}Z"
                        else:
                            raw = f"{raw}Z"
                    ts_utc = datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S.%fZ")
                    ts_utc = utc.localize(ts_utc)
                    ts_local = ts_utc.astimezone(local_tz)
                    date_str = ts_local.date().isoformat()
                    time_str = ts_local.strftime("%H:%M:%S")
                except Exception:
                    # fallback to last_modified below
                    pass

            if not date_str or not time_str:
                ts_local = last_modified_utc.astimezone(local_tz)
                date_str = ts_local.date().isoformat()
                time_str = ts_local.strftime("%H:%M:%S")

            # SAS URL
            sas_token = generate_sas_token(container_name, blob_path)
            blob_url = (
                f"https://{blob_service_client.account_name}.blob.core.windows.net/"
                f"{container_name}/{blob_path}?{sas_token}"
            )

            # Flag whether this file is vectorized (videos -> no)
            ext = os.path.splitext(file.filename)[1].lower()
            in_vector = "yes" if ext in text_exts else "no"

            files_with_links.append(
                {
                    "course_name": container_name,
                    "domain": domain_name,
                    "name": file.filename,
                    "url": blob_url,
                    "blob_name": blob_path,
                    "version_id": version_id,
                    "date_str": date_str,
                    "time_str": time_str,
                    "in_vector_store": in_vector,
                    "is_root_blob": "yes",
                }
            )

            activities.append(
                {
                    "uername": username,
                    "course_name": collection_name,
                    "domain": domain_name,
                    "file": file.filename,
                    "action": "Uploaded File",
                    "date_str": date_str,
                    "time_str": time_str,
                }
            )

        create_document_success = create_document(files_with_links)
        if create_document_success:
            if add_activity(activities):
                return jsonify({"message": "Documents created successfully!"}), 201
            else:
                return jsonify({"error": "Failed to upload activity status"}), 500
        else:
            return jsonify({"error": "Failed to create documents"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/deletecourse", methods=["DELETE"])
def delete_course():
    data = request.json
    collection_name = data.get("collectionName")
    collection_name = collection_name.lower().replace(" ", "-")
    if not collection_name:
        return jsonify({"error": "Collection name is required"}), 400
    try:
        delete_index = delete_index_function(collection_name)
        if delete_index:
            delete_success_container = delete_blob_storage_container(collection_name)
            if delete_success_container:
                delete_all_course_docs = delete_all_course_documents(collection_name)
                if delete_all_course_docs:
                    return (
                        jsonify({"message": "Container deleted successfully!"}),
                        201,
                    )
                else:
                    return jsonify(
                        {"message: Failed to delete the documents"}), 500
            else:
                return jsonify({"error": "Failed to delete contaier"}), 500
        else:
            return jsonify({"error": "Failed to delete index"}), 500

    except Exception as error:
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/deletedomain", methods=["DELETE"])
def delete_domain():
    data = request.json
    course_name = data.get("collectionName")
    domain_name = data.get("domainName")
    username = data.get("username")
    activities = []
    try:
        domain_docs = get_documents(username, course_name, domain_name)
        for doc in domain_docs:
            deletion_status = delete_embeddings_function(doc["name"], course_name)
            if not deletion_status:
                return (
                    jsonify({"message: Failed to delete embeddings"}),
                    500,
                )

        delete_success_domain_folder = delete_domain_virtual_folder(
            course_name, domain_name
        )
        if delete_success_domain_folder:
            delete_success_domain_docs = delete_domain_docs(course_name, domain_name)
            if delete_success_domain_docs:
                timestamp_dt = utc.localize(datetime.utcnow())
                local_tz = timezone("Asia/Singapore")
                local_timestamp_dt = timestamp_dt.astimezone(local_tz)

                date_str = local_timestamp_dt.date().isoformat()
                time_str = local_timestamp_dt.strftime("%H:%M:%S")

                activities.append(
                    {
                        "uername": username,
                        "course_name": course_name,
                        "domain": domain_name,
                        "file": "null",
                        "action": "Deleted Domain",
                        "date_str": date_str,
                        "time_str": time_str,
                    }
                )

                add_activity_status = add_activity(activities)

                if add_activity_status:
                    return jsonify({"message": "Domain deleted successfully!"}), 201
                else:
                    return jsonify(
                        {"message: Failed to add activity status"}), 500

            else:
                return jsonify(
                    {"message: Failed to delete the domain documents"}), 500
        else:
            return jsonify({"error": "Failed to delete contaier"}), 500
    except Exception as error:
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/<collection_name>/<domain_name>/deletedocument", methods=["DELETE"])
def delete_file(collection_name, domain_name):
    data = request.json
    file_name = data.get("fileName")
    file_id = data.get("_id")
    version_id = data.get("versionId")
    is_root_blob = data.get("isRootBlob")
    container_name = collection_name.lower().replace(" ", "-")
    username = data.get("username")
    action = data.get("action")

    activities = []

    try:
        delete_success = delete_from_azure_blob_storage(
            container_name, file_name, domain_name, version_id, is_root_blob
        )
        if delete_success:
            delete_document_success = delete_document(
                collection_name, file_id, is_root_blob, file_name
            )
            if delete_document_success:
                timestamp_dt = utc.localize(datetime.utcnow())
                local_tz = timezone("Asia/Singapore")
                local_timestamp_dt = timestamp_dt.astimezone(local_tz)

                date_str = local_timestamp_dt.date().isoformat()
                time_str = local_timestamp_dt.strftime("%H:%M:%S")

                activities.append(
                    {
                        "uername": username,
                        "course_name": container_name,
                        "domain": domain_name,
                        "file": file_name,
                        "action": action,
                        "date_str": date_str,
                        "time_str": time_str,
                    }
                )

                add_activity_status = add_activity(activities)
                if add_activity_status:
                    return jsonify({"message": "Document deleted successfully!"}), 201
                else:
                    return jsonify({"error": "Failed to add activity"}), 500

            else:
                return jsonify({"error": "Failed to delete document"}), 500
        else:
            return jsonify(
                {"error": "Failed to upload file to Azure Blob Storage"}), 500
    except Exception as error:
        print(f"Error processing file upload: {error}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/api/<collection_name>/deleteembeddings", methods=["DELETE"])
def DeleteEmbeddings(collection_name):
    data = request.json
    blobName = data.get("fileName")

    embeddings_delete_status = delete_embeddings_function(blobName, collection_name)

    if embeddings_delete_status:
        return jsonify({"message": "Embeddings deleted successfully"}), 201
    else:
        return jsonify({"message": "Failed to delete embeddings"}), 500


@app.route("/updatemovement", methods=["PUT"])
def update_movement():
    data = request.json
    collection_name = data.get("collectionName")
    domain_name = data.get("domainName")
    file_name = data.get("fileName")
    version_id = data.get("versionId")
    username = data.get("username")

    activities = []

    try:
        create_document_success = update_movement_document(
            collection_name, file_name, version_id
        )
        if create_document_success:
            timestamp_dt = utc.localize(datetime.utcnow())
            local_tz = timezone("Asia/Singapore")
            local_timestamp_dt = timestamp_dt.astimezone(local_tz)

            date_str = local_timestamp_dt.date().isoformat()
            time_str = local_timestamp_dt.strftime("%H:%M:%S")

            activities.append(
                {
                    "uername": username,
                    "course_name": collection_name,
                    "domain": domain_name,
                    "file": file_name,
                    "action": "Moved to vector store",
                    "date_str": date_str,
                    "time_str": time_str,
                }
            )

            add_activity_status = add_activity(activities)

            if add_activity_status:
                return jsonify({"message": "Documents created successfully!"}), 201
            else:
                return jsonify({"error": "Failed to add activity"}), 500

        else:
            return jsonify({"error": "Failed to create documents"}), 500

    except Exception as error:
        print(f"Error processing files upload: {error}")
        return jsonify({"error": "Internal server error"}), 500


@app.route("/get-chats", methods=["GET"])
def get_chats():
    chats = get_chatlogs()
    return jsonify(chats), 201


@app.route("/manageaccess/<course_name>", methods=["GET"])
def getCourseUsers(course_name):
    usersList = get_course_users(course_name)
    if usersList is False:
        return jsonify({"message": "Error fetching users of this course"}), 500
    else:
        return jsonify(usersList), 201


@app.route("/manageaccess/deleteUser", methods=["DELETE"])
def deleteCourseUsers():
    data = request.json
    course_name = data.get("collectionName")
    user = data.get("username")

    deletionStatus = delete_course_user(course_name, user)
    if deletionStatus:
        return jsonify({"message": "Successfully revoked access to the user"}), 201
    else:
        return jsonify({"message": "Coul not revoke access to the user"}), 500


@app.route("/api/<course_name>/totalFiles", methods=["GET"])
def getTotalCourseFiles(course_name):
    courseFilesCount = get_course_files_count(course_name)
    if courseFilesCount == "False":
        return jsonify({"message": "Error fetching files count"}), 500
    else:
        return jsonify(courseFilesCount), 201


@app.route("/api/<course_name>/<domain_name>/totalFiles", methods=["GET"])
def getTotalDomainFiles(course_name, domain_name):
    domainFilesCount = get_domain_files_count(course_name, domain_name)
    if domainFilesCount == "False":
        return jsonify({"message": "Error fetching files count"}), 500
    else:
        return jsonify(domainFilesCount), 201


@app.route("/chats/totalUsers/<username>", methods=["GET"])
def getTotalUsers(username):
    usersCount = get_users_count(username)
    if usersCount == "False":
        return jsonify({"message": "Error fetching files count"}), 500
    else:
        return jsonify(usersCount), 201


@app.route("/chats/totalQueries/<username>", methods=["GET"])
def getTotalQueries(username):
    queriesCount = get_queries_count(username)
    if queriesCount == "False":
        return jsonify({"message": "Error fetching files count"}), 500
    else:
        return jsonify(queriesCount), 201


@app.route("/chats/queriesByMonth/<username>", methods=["GET"])
def getQueriesByMonth(username):
    queries_by_month = get_queries_by_month(username)
    if queries_by_month == "False":
        return jsonify({"message": "Error fetching files count"}), 500
    else:
        return queries_by_month, 201


@app.route("/chats/queriesByCourse/<username>", methods=["GET"])
def getQueriesByCourse(username):
    queries_by_course = get_queries_by_course(username)
    if queries_by_course == "False":
        return jsonify(
            {"message": "Error fetching query count by course"}), 500
    else:
        return queries_by_course, 201


@app.route("/chats/userSentiments/<username>", methods=["GET"])
def getUserSentiments(username):
    user_sentiments = get_user_sentiments(username)
    if user_sentiments == "False":
        return jsonify({"message": "Error fetching user sentiments"}), 500
    else:
        return user_sentiments, 201


@app.route("/chats/userEmotions/<username>", methods=["GET"])
def getUserEmotions(username):
    user_emotions = get_user_emotions(username)
    if user_emotions == "False":
        return jsonify({"message": "Error fetching user emotions"}), 500
    else:
        return user_emotions, 201


@app.route("/invite", methods=["POST"])
def invite_user():
    data = request.get_json()
    email = data.get("email")
    courseName = data.get("course")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    token = get_access_token()

    if not token:
        return jsonify({"error": "Unable to acquire access token"}), 500

    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    if check_if_rec_exists(email, courseName):
        return jsonify({"error": "User already has access to this folder"}), 500

    user_check_url = (
        graph_url
        + f"users?$filter=mail eq '{email}' or userPrincipalName eq '{email}'"
    )
    user_response = requests.get(user_check_url, headers=headers)

    if user_response.status_code == 200:
        user_data = user_response.json()

        if len(user_data.get("value", [])) > 0:
            upload_status = upload_course(courseName, email)
            if upload_status:
                return (
                    jsonify({"message": "User added to access this course"}),
                    201,
                )
            else:
                return jsonify({"error": "Error in adding user"}), 500

        else:
            invite_url = graph_url + "invitations"
            invite_body = {
                "invitedUserEmailAddress": email,
                "inviteRedirectUrl": "https://asknarelle-frontend.azurewebsites.net",
                "sendInvitationMessage": True,
            }

            invite_response = requests.post(
                invite_url, headers=headers, json=invite_body
            )
            print(invite_response.text)
            print(invite_response.status_code)
            if invite_response.status_code == 201:
                upload_course(courseName, email)
                return (
                    jsonify({"message": "Invitation sent successfully!"}),
                    201,
                )
            else:
                print(invite_response.json())
                return (
                    jsonify({"error": invite_response.json()}),
                    invite_response.status_code,
                )
    else:
        print(user_response.json())
        return jsonify({"error": user_response.json()}), user_response.status_code


@app.route("/activities/<username>/viewactivities", methods=["GET"])
def get_activities(username):
    print(username)
    activities = view_activities(username)
    if activities is not False:
        return jsonify(activities), 201
    else:
        return jsonify({"message": "Error fetching activities"}), 500


@app.route("/vi/courses", methods=["POST"])
def vi_create_course():
    data = request.get_json(silent=True) or {}
    course_code = data.get("courseCode") or ""
    course_name = data.get("courseName") or ""
    description = data.get("description") or ""
    collection_name = data.get("collectionName")
    username = data.get("username")

    if not course_code:
        return jsonify({"error": "courseCode is required"}), 400

    # code is similar to createcollection API, except this creates our course in Azure Cosmos DB
    created = createContainer(course_code)
    if not created:
        return jsonify({"error": "Container already exists"}), 409

    if not upload_course(collection_name, username):
        return jsonify(
            {"error": "Failed to register course in file_database"}), 500

    vi_status = "created"
    vi_payload = None
    try:
        successful = vi_add_course(
            course_code=course_code,
            course_name=course_name,
            description=description,
            owner_username=username,
        )
    except Exception as e:
        msg = str(e)
        if "duplicate" in msg.lower():
            vi_status = "exists"
        else:
            vi_status = "error"

    if successful:
        return (
            jsonify(
                {
                    "message": "Course created",
                    "courseCode": course_code,
                    "viCourseStatus": vi_status,
                    "viCourse": vi_payload,
                }
            ),
            201,
        )

@app.route("/vi/videos", methods=["POST"])
def vi_upload_videos():
    body = request.get_json(silent=True) or {}
    course_code = (body.get("courseCode") or "").strip()
    videos = body.get("video") or []

    if not course_code:
        return jsonify({"error": "courseCode is required"}), 400
    if not isinstance(videos, list) or len(videos) == 0:
        return jsonify({"error": "video must be a non-empty list"}), 400

    course_doc = check_if_course_exist(course_code)
    if not course_doc:
        return jsonify({"error": f"Course not found: {course_code}"}), 404
    
    course_id = course_doc["_id"]
    registered = []
    errors = []

    for idx, v in enumerate(videos):
        name = (v.get("video_name") or "").strip()
        b64 = (v.get("base64_encoded_video") or "").strip()
        desc = (v.get("video_description") or "").strip()
        user_email = (body.get("username") or "").strip()

        if not name or not b64:
            errors.append({"index": idx, "error": "Missing name or video data"})
            continue

        try:
            vd = VideoDetails(video_name=name, video_description=desc, video_id="")
            video_oid = insert_video_indexing_progress(vd, course_id)

            t = threading.Thread(
                target=index_video_and_update_metadata,
                kwargs={
                    "course_doc": course_doc,
                    "video_object_id": video_oid,
                    "video_name": name,
                    "base64_encoded_video": b64,
                    "video_description": desc,
                    "user_email": user_email
                }
            )
            t.start()

            registered.append({
                "video_mongo_id": str(video_oid), 
                "video_name": name,
                "status": "IN_PROGRESS"
            })

        except Exception as e:
            errors.append({"index": idx, "error": str(e)})

    return jsonify({
        "courseCode": course_code, 
        "registered": registered, 
        "errors": errors,
        "message": "Uploads started in background."
    }), 201

@app.route("/api/vi/status/<course_code>", methods=["GET"])
def get_video_statuses(course_code):
    try:
        all_courses = get_course_videos_manage(course_code)
        if not all_courses:
            return jsonify({}), 200

        target_course = all_courses[0]
        status_map = {}
        for v in target_course.get("courseVideos", []):
            name = v.get("videoName")
            status = v.get("status")
            vi_id = v.get("_id") # Internal VI Mongo ID
            
            if name:
                status_map[name] = {
                    "status": status,
                    "vi_mongo_id": vi_id 
                }

        return jsonify(status_map), 200
    except Exception as e:
        print(f"Error fetching statuses: {e}")
        return jsonify({}), 500

@app.route("/api/vi/delete_video", methods=["DELETE"])
def delete_video_indexer_entry():
    """
    Expects { "id": "VI_MONGO_ID" }
    """
    try:
        body = request.get_json(silent=True) or {}
        mongo_id = body.get("id")
        if not mongo_id: return jsonify({"error": "ID required"}), 400

        # 1. Look up doc to find External Azure ID
        doc = get_video_document_by_id(mongo_id)
        if doc and doc.get("video_id"):
            try:
                # 2. Delete from Azure
                VideoIndexerClient().delete_video(doc.get("video_id"))
            except Exception as e:
                print(f"Azure Delete Warning: {e}")

        # 3. Delete from VI MongoDB
        if delete_video_entry_from_db(mongo_id):
            return jsonify({"message": "Deleted successfully"}), 200
        else:
            return jsonify({"error": "Database deletion failed"}), 500

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route("/chat/<video_id>", methods=["POST"])
def chat_with_video(video_id):
    """
    Endpoint to chat with a specific video's knowledge base.
    Expects JSON body: { "message": "...", "previous_messages": [...], "video_ids": [], "course_code": "" }
    """
    try:
        # 1. Get JSON data from Flask
        data = request.get_json()
        
        # 2. Validate and Parse using the Pydantic model from chat_helper
        # This automatically converts the list of dicts into ChatHistory objects
        body = ChatRequestBody(**data) 
        
        # 3. Call the helper function
        # We pass the cleaned Pydantic objects to the helper
        answer = chat_client.generate_response(
            video_id=video_id, 
            message=body.message, 
            previous_messages=body.previous_messages,
            video_ids=body.video_ids, 
            course_code=body.course_code 
        )
        
        return jsonify({"answer": answer}), 200

    except Exception as e:
        print(f"Chat error for video {video_id}: {e}")
        # If Pydantic validation fails, it usually raises a ValidationError
        return jsonify({"error": str(e)}), 500

@app.route("/api/chat/course", methods=["POST"])
def chat_with_course():
    """
    Unified Endpoint for Chatting with Course (Docs + Video).
    Flow: Docs -> Video
    """
    try:
        data = request.get_json()
        body = ChatRequestBody(**data) 
        
        target_video_ids = body.video_ids
        course_code = body.course_code
        message = body.message

        # 1. Search Documents (Azure AI Search)
        # Note: 'course_code' matches your 'containername' / index name in AI Search
        print(f"Searching documents for course: {course_code}...")
        # Use a reasonable threshold (0.65 - 0.7) for ADA-002 models
        doc_matches = search_documents(course_code, message, top_k=3, score_threshold=5)
        
        if doc_matches:
            print(f"Found {len(doc_matches)} document matches. Generating answer from docs...")
            answer = chat_client.generate_answer_from_docs(
                context_list=doc_matches,
                message=message,
                previous_messages=body.previous_messages
            )
            if answer:
                return jsonify({"answer": answer, "source": "documents"}), 200
        
        # 2. Fallback to Video Search (Existing Logic)
        print("No sufficient document matches. Falling back to Video Indexer...")
        
        if not target_video_ids and course_code:
            target_video_ids = get_all_video_ids_for_course(course_code)
            
            if not target_video_ids:
                # If both docs and videos fail
                return jsonify({"answer": f"I couldn't find any relevant documents or processed videos for course {course_code}."}), 200

        answer = chat_client.generate_response(
            message=message, 
            previous_messages=body.previous_messages,
            video_ids=target_video_ids,
            course_code=course_code
        )
        
        return jsonify({"answer": answer, "source": "video"}), 200

    except Exception as e:
        print(f"Chat error: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)