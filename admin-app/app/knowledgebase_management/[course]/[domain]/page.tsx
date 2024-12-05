"use client";

import React from 'react';
import { useState, useEffect } from 'react';
import DocumentPopup from '../../../components/course_files/DocumentPopup';
import { AiOutlineFileAdd } from "react-icons/ai";
import { useSearchParams } from 'next/navigation';
import FileCard from '../../../components/course_files/FileCard';
import { CiSearch } from "react-icons/ci";
import FileDeletionPopup from '../../../components/course_files/FileDeletionPopup';
import FileMovementPopup from '../../../components/course_files/FileMovementPopup';
import BlobDeletionPopup from '../../../components/course_files/BlobDeletionPopup';
import { Suspense } from 'react';
import FilesTable from '../../../components/course_files/FilesTable';
import withAuth from "../../../components/authentication/WithAuth";
import { msalConfig } from "@/authConfig";
import { PublicClientApplication} from "@azure/msal-browser";
import NotFoundPage from '../../../components/authentication/404';
import ForbiddenPage from '../../../components/authentication/403';

interface Document{
    _id: string;
    name: string;
    url: string;
    version_id: string;
    blob_name: string;
    domain: string;
    date_str: string;
    time_str: string;
    in_vector_store: string;
    is_root_blob: string;
    course_name: string
}

const msalInstance = new PublicClientApplication(msalConfig);

function Fileslist({params} : {params: {domain: string, course: string}}): JSX.Element{
    const [message, setMessage] = useState<Document[]>([]);
    const [showPopup, setShowPopup] = useState<boolean>(false);
    const [fileCreated, setFileCreated] = useState<boolean>(true); 
    const [fileDeleted, setFileDeleted] = useState<boolean>(true); 
    const [fileMoved, setFileMoved] = useState<boolean>(true);
    const [blobDeleted, setBlobDeleted] = useState<boolean>(true);
    const [searchQuery, setSearchQuery] = useState<string>('');
    const [showDeletionPopup, setShowDeletionPopup] = useState<boolean>(false);
    const [showFileMovementPopup, setShowFileMovementPopup] = useState<boolean>(false);
    const [showBlobDeletionPopup, setShowBlobDeletionPopup] = useState<boolean>(false);
    const[fileName, setFileName] = useState<string>('');
    const[collection, setCollection] = useState<string>('');
    const[docId, setDocId] = useState<string>('');
    const[versionId, setVersionId] = useState<string>('');
    const[isRootBlob, setIsRootBlob] = useState<string>('');
    const[authorised, setAuthorised] = useState<boolean>(true)
    const[coursePresent, setCoursePresent] = useState<boolean>(true)

    const searchParams = useSearchParams();
    const collectionName = params.course//searchParams.get("course") || '';
    const domainName = params.domain//searchParams.get("domain") || '';

    const accounts = msalInstance.getAllAccounts();
    const username = accounts[0]?.username; 
  
    const handleFileCreated = () => {
      setFileCreated(!fileCreated);
    };

    const handleFileDeleted = () => {
      setFileDeleted(!fileDeleted);
    };

    const handleFileMoved = () => {
      setFileMoved(!fileMoved)
    }

    const handleBlobDeleted = () => {
      setBlobDeleted(!blobDeleted)
    }
  
    const handleButtonClick = (): void => {
      setShowPopup(true);
    };
  
    const handleClosePopup = (): void => {
      setShowPopup(false);
    };

    const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
      setSearchQuery(event.target.value);
    };

    const handlePressDelete = (id: string, collection: string, file: string, version_id: string, is_root_blob: string) => {
       setFileName(file);
       setCollection(collection);
       setDocId(id);
       setShowDeletionPopup(true)
       setVersionId(version_id)
       setIsRootBlob(is_root_blob)
    }

    const handlePressMovement = (id: string, collection: string, file: string, version_id: string) => {
      setFileName(file);
      setCollection(collection);
      setDocId(id);
      setShowFileMovementPopup(true)
      setVersionId(version_id)
   }

   const handlePressBlobDelete = (id: string, collection: string, file: string, version_id: string, is_root_blob: string) => {
    setFileName(file);
    setCollection(collection);
    setDocId(id);
    setShowBlobDeletionPopup(true)
    setVersionId(version_id)
    setIsRootBlob(is_root_blob)
 }

    const handleCloseDeletionPopup = (): void => {
      setShowDeletionPopup(false);
    }

    const handleCloseFileMovementPopup = (): void => {
      setShowFileMovementPopup(false);
    }

    const handleCloseBlobDeletePopup = (): void => {
      setShowBlobDeletionPopup(false);
    }

  
    useEffect(() => {
      // console.log("Document");
        fetch(`https://asknarelle-backend.azurewebsites.net/api/collections/${username}/${collectionName}/${domainName}`)
        .then(response => {
          if (response.status === 403) {
            setAuthorised(false)
          }
          else if(response.status === 404){
            setCoursePresent(false)
          }
          else if (response.status === 500){
            throw new Error('Failed to fetch course domains');
          }
          else{
            return response.json();
          }
        })
        .then((documents: Document[]) => {
          setMessage(documents);
        })
        .catch(error => {
          console.error('Error fetching collections:', error);
        });
    }, [fileCreated, fileDeleted, collectionName, blobDeleted, fileMoved, domainName, username]); 

    const filteredFiles = message?.filter(document =>
      document?.name?.toLowerCase().includes(searchQuery.toLowerCase())
    );
  
  
    return (
      <main className="flex h-screen mt-[8vh] lg:mt-[0vh] flex-col p-10 sm:p-24 bg-gray-100">
        <div className="flex flex-row justify-between">
          {
            authorised && coursePresent &&
          
        <div className="font-semibold relative w-10 text-xl font-nunito">
          {collectionName}
          <div className="absolute left-2 w-full h-1 bg-[#3C456C]"></div>
        </div>
}
         <div>
          {authorised && coursePresent && message?.length > 0 &&  <button onClick={handleButtonClick} className="bg-[#2C3463] text-white py-2 px-4 rounded-lg font-normal transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C] font-nunito">Add New File</button>}
         </div>
        </div>
        {
          coursePresent ? (
            authorised ? (
        message?.length > 0 ? (
          <>
           <div className='flex items-center justify-center mt-5 sm:mt-0'>
           <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={handleSearchChange}
              placeholder="Search for Files"
              className="border border-gray-300 rounded-lg py-2 pl-10 pr-4 mr-2 w-full font-nunito"
            />
            <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <CiSearch size={20} />
            </div>
          </div>
        </div> 
           <FilesTable files={filteredFiles} collectionName={collectionName} onFileDeleted={handlePressDelete} onFileMoved={handlePressMovement} onBlobDeleted={handlePressBlobDelete}/>
        </>
      ) : (
        <div className="flex h-screen flex-col items-center justify-center">
          <div className="flex flex-col bg-white sm:w-4/5 w-full border border-dotted border-[#3F50AD] p-4 mx-auto rounded-lg items-center">
            <AiOutlineFileAdd size={50} color="#2C3463" />
            <p className="font-semibold text-lg mt-2 font-nunito">Upload the materials</p>
            <button
              onClick={handleButtonClick}
              className="bg-[#2C3463] text-white py-2 px-4 rounded-lg font-normal mt-5 sm:w-2/5 w-full  transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C] font-nunito"
            >
              Add New Files
            </button>
          </div>
        </div>
      )) : (
        <ForbiddenPage/>
      )) : (
        <NotFoundPage/>
      )}
        {showPopup && <DocumentPopup onClose={handleClosePopup} onFileCreated={handleFileCreated} collectionName = {collectionName} domainName={domainName} username={username}/>}
        {showDeletionPopup && <FileDeletionPopup fileName={fileName} collectionName={collection} id={docId} onFileDeleted={handleFileDeleted} onClose={handleCloseDeletionPopup} domainName={domainName} version_id={versionId} is_root_blob={isRootBlob} username={username}/>}
        {showFileMovementPopup && <FileMovementPopup fileName={fileName} collectionName={collection} id={docId} onFileMoved={handleFileMoved} onClose={handleCloseFileMovementPopup} domainName={domainName} version_id={versionId} username={username}/>}
        {showBlobDeletionPopup && <BlobDeletionPopup fileName={fileName} onBlobDeleted={handleBlobDeleted} id={docId} collectionName={collection} onClose={handleCloseBlobDeletePopup} domainName={domainName} version_id={versionId} is_root_blob={isRootBlob} username={username}/>}
      </main>
    );
};

const AuthenticatedFilesList= withAuth(Fileslist);

export default function FilePage({params}: {params: {domain: string, course: string}}): JSX.Element {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AuthenticatedFilesList params={params}/>
    </Suspense>
  );
}