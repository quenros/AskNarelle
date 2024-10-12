import React from 'react';
import { useState, FormEvent } from 'react';
import { IoIosCloseCircleOutline } from "react-icons/io";
import { Oval } from 'react-loader-spinner';
import { AccountInfo } from '@azure/msal-browser';
import { PublicClientApplication} from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";

interface PopupProps {
  onClose: () => void;
  onCourseShared: () => void;
  courseName: string;
}

export const msalInstance = new PublicClientApplication(msalConfig);

const SharePopup: React.FC<PopupProps> = ({ onClose, onCourseShared, courseName}) => {

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0].username;

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setInputValue(e.target.value);
    setErrorMessage(''); // Clear the error message when the input changes
  };
  const [inputValue, setInputValue] = useState('');
  const [message, setMessage] = useState('');


  const handleInvite = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('http://127.0.0.1:5000/invite', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ email: inputValue, course: courseName }),
      });

      const result = await response.json();
      if (response.ok) {
        onCourseShared();
        setMessage('Invitation sent successfully!');
        onClose();
      } else {
        setErrorMessage(`Error: ${result.error}`);
      }
    } catch (error: unknown) {
        // Type guard to check if error is an instance of Error
        if (error instanceof Error) {
          setErrorMessage(`Error: ${error.message}`);
        } else {
          setErrorMessage('An unknown error occurred.');
        }
      } finally {
      setIsLoading(false);
    }
  };


  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-50">
      <div className="bg-white p-8 rounded-lg shadow-md relative sm:w-2/6 w-5/6">
        {!isLoading && (
          <button
            onClick={onClose}
            className="absolute top-0 right-0 p-2"
          >
            <IoIosCloseCircleOutline color='#FF0E0E' size={30}/>
          </button>
        )}
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
            <p className="text-[#1a2d58] text-center mb-4 font-semibold">Sending</p>
          </>
        )}
        {!isLoading && (
          <>
            <label htmlFor="email" className="block mb-2 text-gray-800 font-semibold">User Email{` (Enter the NTU email of the user)`}</label>
            <input
              type="email"
              value={inputValue}
              onChange={handleInputChange}
              className="border border-gray-300 rounded-md px-4 py-2 mb-4 w-full"
              placeholder="Enter NTU email"
            />
            {errorMessage !== ''  && (
              <p className="text-red-500 text-sm mb-4 font-nunito">{errorMessage}</p>
            )}
            <button
              onClick={handleInvite}
              className="bg-[#2C3463] text-white font-bold py-2 px-4 rounded transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]"
            >
              Invite
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default SharePopup;