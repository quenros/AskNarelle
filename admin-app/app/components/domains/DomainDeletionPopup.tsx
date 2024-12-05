import React from 'react';
import { useState } from 'react';
import { Oval } from 'react-loader-spinner';
import { PublicClientApplication} from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";

interface DeletionPopupProps {
  onClose: () => void;
  onCourseDeleted: () => void;
  courseName: string;
  domain: string
}
export const msalInstance = new PublicClientApplication(msalConfig);

const DomainDeletionPopup: React.FC<DeletionPopupProps> = ({ onClose, onCourseDeleted, courseName, domain}) => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0].username;

  const handleDelete = () => {
    setIsLoading(true)
    fetch('https://asknarelle-backend.azurewebsites.net/api/deletedomain', {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ collectionName: courseName, domainName: domain, username: username}),
    })
    .then(response => {
      if (response.status === 201) {
        console.log('Domain deleted successfully')
      } else if(!response.ok) {
        console.error('Failed to delete index');
      }
    })
    .catch(error => {
      console.error('Error deleting course:', error);
    })
    .finally(() => {
      setIsLoading(false);
      onClose();
      onCourseDeleted();
  });
}

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-50">
      <div className="flex flex-col bg-white p-8 rounded-lg shadow-md relative items-center sm:w-2/6 w-5/6">
        {isLoading && (
          <>
            <div className="flex justify-center mb-4">
              <Oval
                height={40}
                width={40}
                color="#2c4787"
                visible={true}
                ariaLabel='oval-loading'
                secondaryColor="#2c4787"
                strokeWidth={2}
                strokeWidthSecondary={2}
              />
            </div>
            <p className="text-[#1a2d58] text-center mb-4 font-semibold">Deleting</p>
          </>
        )}
        {
          !isLoading && (
            <>
                    <p className='font-semibold text-lg'>Are you sure you want to delete the course?</p>
        <p className='text-[#ff3b3b] text-sm'>Warning: Deleting this folder will delete all the content inside</p>
        <div className='flex w-1/2'>
        <button
        onClick={handleDelete}
        className="bg-[#2C3463] text-white font-bold py-2 px-4 rounded mr-5 mt-5 w-2/5 transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]"
        >
        Yes
        </button>
        <button
        onClick={onClose}
        className="bg-[#2C3463] text-white font-bold py-2 px-4 rounded ml-5 mt-5 w-2/5 transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]"
        >
        No
        </button>


        </div></>
          )
        }

      </div>
    </div>
  );
};

export default DomainDeletionPopup;