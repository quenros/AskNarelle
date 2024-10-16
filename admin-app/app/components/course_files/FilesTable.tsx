// FileTable.tsx

import React, {useState} from 'react';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';
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
  const [inVectorStoreFilter, setInVectorStoreFilter] = useState<string | null>(
    null
  );
  const [isRootBlobFilter, setIsRootBlobFilter] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);

  const handleDateConversion = (dateStr: string) => {
    return new Date(dateStr);  
  };

  const filteredFiles = files.filter((document) => {
    const documentDate = handleDateConversion(document.date_str);

    const isWithinDateRange = !startDate || !endDate || 
      (documentDate >= startDate && documentDate <= endDate);

    return (
      (inVectorStoreFilter === null ||
        document.in_vector_store === inVectorStoreFilter) &&
      (isRootBlobFilter === null || document.is_root_blob === isRootBlobFilter) &&
      isWithinDateRange
    );
  });

  return (
    <div className="overflow-scroll mt-5 min-h-full">
      <div className="flex top-0 sticky z-20 justify-center bg-gray-100">
        <div className="flex space-x-4 al">
        <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                In Vector Store?
              </label>
              <select
                className="block w-[50] p-2 text-base border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={inVectorStoreFilter || ''}
                onChange={(e) =>
                  setInVectorStoreFilter(
                    e.target.value === '' ? null : e.target.value
                  )
                }
              >
                <option value="">All</option>
                <option value="yes">Yes</option>
                <option value="no">No</option>
              </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Is Root File?
            </label>
            <select
              className="block w-[50] p-2 text-base border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
              value={isRootBlobFilter || ''}
              onChange={(e) =>
                setIsRootBlobFilter(
                  e.target.value === '' ? null : e.target.value
                )
              }
            >
              <option value="">All</option>
              <option value="yes">Yes</option>
              <option value="no">No</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">Start Date</label>
            <DatePicker
              selected={startDate}
              onChange={(date) => setStartDate(date)}
              dateFormat="yyyy-MM-dd"
              className="mt-1 p-2 border border-gray-300 rounded-md"
              placeholderText="Select start date"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">End Date</label>
            <DatePicker
              selected={endDate}
              onChange={(date) => setEndDate(date)}
              dateFormat="yyyy-MM-dd"
              className="mt-1 p-2 border border-gray-300 rounded-md"
              placeholderText="Select end date"
            />
          </div>
       
        </div>
      </div>
      <table className="min-w-full divide-y divide-gray-200 rounded-lg mb-5 mt-5">
       <thead className="bg-[#2C3463] top-16 sticky z-10">
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
          {filteredFiles.map((document: Document, index: number) => (
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
