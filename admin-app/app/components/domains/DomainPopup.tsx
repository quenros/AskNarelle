import React from 'react';
import { useState } from 'react';
import { IoIosCloseCircleOutline } from "react-icons/io";
import { Oval } from 'react-loader-spinner';
import { PublicClientApplication} from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";


interface PopupProps {
  onClose: () => void;
  onDomainCreated: () => void;
  collectionName: string
  
}

export const msalInstance = new PublicClientApplication(msalConfig);

const DomainPopup: React.FC<PopupProps> = ({ onClose, onDomainCreated, collectionName}) => {
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [errorMessage, setErrorMessage] = useState<string>('');
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0].username;


 
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    
    // Regular expression to allow only lowercase letters and numbers
    const regex = /^[a-z0-9]*$/;

    // If the input is valid, update the input value and clear the error message
    if (regex.test(value)) {
      setInputValue(value);
      setErrorMessage('');
    } else {
      // Show error message for invalid input
      setErrorMessage('Input can only contain lowercase letters and numbers.');
    }
  };


  const handleSubmit = () => {
    setIsLoading(true)
    fetch('https://asknarelle-backend.azurewebsites.net/api/createdomain', {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ domainName: inputValue, courseName: collectionName, user: username, action: "Domain Creation"}),
    })
    .then(response => {
      if (response.ok) {
        console.log('Domain created successfully');
        onClose();
        onDomainCreated(); 
      } 
      else if(response.status === 400){
        return response.json().then(data => {
          setErrorMessage(data.message); // Use the message from the response
        });
      }
      else {
        throw new Error('Failed to create domain');
      }
    })
    .catch(error => {
      console.error('Error creating domain:', error);
    })
    .finally(() => {
      setIsLoading(false);
     // Close the popup regardless of success or failure
    });
  };
  
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-50">
      <div className="bg-white p-8 rounded-lg shadow-md relative sm:w-2/6 w-5/6">
        { !isLoading && (
           <button
           onClick={onClose}
           className="absolute top-0 right-0 p-2"
         >
          <IoIosCloseCircleOutline color='#FF0E0E' size={30}/>
         </button>

        )
        }
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
            <p className="text-[#1a2d58] text-center mb-4 font-semibold">Creating</p>
          </>
        )}
        {
          !isLoading && (
            <>
            <label htmlFor="courseName" className="block mb-2 text-gray-800 font-semibold">Category Name</label>
            <input
              type="text"
              value={inputValue}
              onChange={handleInputChange}
              className="border border-gray-300 rounded-md px-4 py-2 mb-4 w-full"
              placeholder="Enter your input"
            />
             {errorMessage !== ''  && (
              <p className="text-red-500 text-sm mb-4 font-nunito">{errorMessage}</p>
            )}
            <button
              onClick={handleSubmit}
              className="bg-[#2C3463] text-white font-bold py-2 px-4 rounded transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]"
            >
              Submit
            </button>
            </>

          )
        }

      </div>
    </div>
  );
};

export default DomainPopup;