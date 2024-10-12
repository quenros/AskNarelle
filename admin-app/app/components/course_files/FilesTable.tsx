// FileTable.tsx

import React from 'react';
import FileCard from './FileCard';

interface Document{
    _id: string;
    name: string;
    url: string;
    version_id: string;
    date_str: string;
    time_str: string;
    in_vector_store: string;
    is_root_blob: string
}

interface FileTableProps {
  files: Document[];
  collectionName: string;
  onFileDeleted: (id: string, collection: string, file: string, version_id: string, is_root_blob: string) => void,
  onFileMoved: (id: string, collection: string, file: string, version_id: string) => void,
  onBlobDeleted: (id: string, collection: string, file: string, version_id: string, is_root_blob: string) => void
}

const FilesTable: React.FC<FileTableProps> = ({
  files,
  collectionName,
  onFileDeleted,
  onFileMoved,
  onBlobDeleted,
}) => {
  return (
    <div className="overflow-scroll mt-5">
      <table className="min-w-full divide-y divide-gray-200 rounded-lg">
       <thead className="bg-[#2C3463] sticky top-0 z-10">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              File Name
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              In Vector Store ?
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Is Root File ?
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Date
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Time
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Actions 
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {files.map((document: Document, index: number) => (
            <tr key={index}>
              <td className="px-6 py-4 whitespace-nowrap">
              <a href={document.url} download={document.name} className="text-blue-600 text-center underline font-nunito text-sm">
              {document.name}
               </a>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{document.in_vector_store.toString()}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{document.is_root_blob.toString()}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{document.date_str}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{document.time_str}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap text-sm font-medium font-nunito">
              { (document.in_vector_store === "yes" || document.is_root_blob === "yes") && (
                <button
                  className="text-red-500 mr-5 p-2 transition duration-300 transform hover:scale-105 rounded-xl bg-red-500 bg-opacity-20"
                  onClick={() => onFileDeleted(document._id, collectionName, document.name, document.version_id, document.is_root_blob)}
                >
                  Delete
                </button> )}
                { (document.in_vector_store === "no" && document.is_root_blob === "no") && (
                    <>
                     <button
                     className="text-orange-500 mr-5 p-2 transition duration-300 transform hover:scale-105 rounded-xl bg-orange-500 bg-opacity-20"
                     onClick={() => onBlobDeleted(document._id, collectionName, document.name, document.version_id, document.is_root_blob)}
                   >
                     Delete From File Storage
                   </button>
                <button
                  className="text-green-500 mr-5 border border-solid p-2 transition duration-300 transform hover:scale-105 rounded-xl bg-green-500 bg-opacity-20"
                  onClick={() => onFileMoved(document._id, collectionName, document.name, document.version_id)}
                >
                  Move to vector store
                </button> 
                </>)}
                { (document.in_vector_store === "no" && document.is_root_blob === "yes") && (
                    <>
            {/* <button
            className="text-red-500 mr-5 p-2 transition duration-300 transform hover:scale-105 rounded-xl bg-red-500 bg-opacity-20"
            onClick={() => onFileDeleted(document._id, collectionName, document.name, document.version_id, document.is_root_blob)}
          >
            Delete
          </button>  */}
                     <button
                     className="text-green-500 mr-5 p-2 transition duration-300 transform hover:scale-105 rounded-xl bg-green-500 bg-opacity-20"
                     onClick={() => onFileMoved(document._id, collectionName, document.name, document.version_id)}
                   >
                     Move to vector store
                   </button>
                   </> )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default FilesTable;
