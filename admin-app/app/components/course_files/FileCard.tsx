"use client";

import React,{useState} from 'react';

interface FileProps{
    fileName: string,
    collectionName: string,
    id: string,
    url: string,
    version_id: string,
    date: string,
    time: string,
    in_vector_store: string,
    is_root_blob: string,
    onFileDeleted: (id: string, collection: string, file: string, version_id: string, is_root_blob: string) => void,
    onFileMoved: (id: string, collection: string, file: string, version_id: string) => void,
    onBlobDeleted: (id: string, collection: string, file: string, version_id: string, is_root_blob: string) => void
}

const FileCard: React.FC<FileProps> = ({fileName, collectionName, id, onFileDeleted, url, date, time, version_id, in_vector_store,is_root_blob, onBlobDeleted, onFileMoved}) => {

  return (
    <div className='border border-black rounded-lg shadow-lg px-7 py-3 mr-5 mt-5 flex w-1/2 justify-between'>
          <a href={url} download={fileName} className="text-blue-600 text-center underline">
              {fileName}
          </a>
          <p>{is_root_blob}</p>
          <p>{date}</p>
          <p>{time}</p>
        { (in_vector_store === "yes") && (
              <button className='border border-red-400 rounded-lg px-3 text-red-400 transition-transform duration-300 ease-in-out transform hover:scale-105 '  onClick={() => onFileDeleted(id, collectionName, fileName, version_id, is_root_blob)}>Delete</button>

             )
        }
        { (in_vector_store === "no" && is_root_blob === "no") && (
              <>
              <button className='border border-red-400 rounded-lg px-3 text-red-400 transition-transform duration-300 ease-in-out transform hover:scale-105 '  onClick={() => onBlobDeleted(id, collectionName, fileName, version_id, is_root_blob)}>Delete from file storage</button>
             <button className='border border-red-400 rounded-lg px-3 text-red-400 transition-transform duration-300 ease-in-out transform hover:scale-105 '  onClick={() => onFileMoved(id, collectionName, fileName, version_id)}>Move to vector store</button> 
             </>

             )
        }
         { (in_vector_store === "no" && is_root_blob === "yes") && (
              <>
             <button className='border border-red-400 rounded-lg px-3 text-red-400 transition-transform duration-300 ease-in-out transform hover:scale-105 '  onClick={() => onFileDeleted(id, collectionName, fileName, version_id, is_root_blob)}>Delete</button>
             <button className='border border-red-400 rounded-lg px-3 text-red-400 transition-transform duration-300 ease-in-out transform hover:scale-105 '  onClick={() => onFileMoved(id, collectionName, fileName, version_id)}>Move to vector store</button> 
             </>

             )
        }
       
    </div>
  );
};

export default FileCard;