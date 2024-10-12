import React from 'react';
import { useState , ChangeEvent, useEffect} from 'react';
import { Oval } from 'react-loader-spinner';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';

interface FileMovementPopupProps {
    fileName: string,
    collectionName: string,
    domainName: string,
    id: string,
    version_id: string,
    onFileMoved: () => void,
    onClose: () => void,
    username: string
}


const FileMovementPopup: React.FC<FileMovementPopupProps> = ({fileName, collectionName, id, onFileMoved, onClose, domainName, version_id, username}) => {
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const[showSliders, setShowSliders] = useState<boolean>(false);
  const[tick, setTick] = useState<boolean>(false);
  const[chunkSize, setChunkSize] = useState<number>(1000);
  const[overlap, setOverlap] = useState<number>(100);


  const handleFileMovement = () => {
    setIsLoading(true);
    fetch(`http://127.0.0.1:5000/movetovectorstore`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(
        { 
        containername: collectionName, 
        domainname: domainName,
        versionid: version_id,
        filename: fileName,
        chunksize: chunkSize,
        overlap: overlap,

     }
        ),
    })
    .then(response => {
      if (response.status === 201) {
        return fetch(`http://127.0.0.1:5000/updatemovement`, {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
              _id: id,
              collectionName: collectionName,
              domainName: domainName,
              fileName: fileName,
              versionId : version_id ,
              username: username
            }),
          });
      } else if(!response.ok) {
        console.error('Failed to delete document');
      }
    })
    .catch(error => {
      console.error('Error deleting document:', error);
    })
    .finally(() => {
        setIsLoading(false);
        onClose();
        onFileMoved();
    });

  }

  const handleCheckboxChange = (e: ChangeEvent<HTMLInputElement>)=> {
    setTick(e.target.checked);
    setShowSliders(e.target.checked);
    
  }


  const handleChunkSliderChange = (value: number | number[]) => {
    if (typeof value === 'number') {
        setChunkSize(value)
    }
  };

  const handleOverlapSliderChange = (value: number | number[]) => {
    if(typeof value === 'number'){
      setOverlap(value)
    }
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-50">
      <div className=" bg-white p-8 rounded-lg shadow-md relative sm:w-2/6 w-5/6">
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
            <p className="text-[#1a2d58] text-center mb-4 font-semibold">Moving File to Vector store</p>
          </>
        )}
        {
          !isLoading && (
            <>
            <p className='font-semibold text-center text-lg'>Are you sure you want to Move this file to vector store?</p>

          
        <div className='flex justify-center'>
        <button
        onClick={handleFileMovement}
        className="bg-[#2C3463] text-white font-bold py-2 px-4 rounded mr-5 mt-5 w-2/12 transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]"
        >
        Yes
        </button>
        <button
        onClick={onClose}
        className="bg-[#2C3463] text-white font-bold py-2 px-4 rounded ml-5 mt-5 w-2/12 transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]"
        >
        No
        </button>


        </div>
        </>
          )
        }
        
      </div>
    </div>
  );
};

export default FileMovementPopup;