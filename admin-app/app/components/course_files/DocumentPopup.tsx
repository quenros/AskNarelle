import React from 'react';
import { useState, ChangeEvent, FormEvent, useEffect } from 'react';
import { IoIosCloseCircleOutline } from "react-icons/io";
import { Oval } from 'react-loader-spinner';
import { FaFileAlt } from 'react-icons/fa';
import Slider from 'rc-slider';
import 'rc-slider/assets/index.css';

interface PopupProps {
  onClose: () => void;
  onFileCreated: () => void;
  collectionName: string;
  domainName: string;
  username: string;
}

interface AiSearchCredential{
   endpoint: string;
   api: string
}

const DocumentPopup: React.FC<PopupProps> = ({ onClose, onFileCreated, collectionName, domainName, username}) => {
  // const [inputValue, setInputValue] = useState('');
  const [files, setFiles] = useState<FileList | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const[showSliders, setShowSliders] = useState<boolean>(false);
  const[tick, setTick] = useState<boolean>(false);
  const[chunkSize, setChunkSize] = useState<number>(1000);
  const[overlap, setOverlap] = useState<number>(100);
  const[progress, setProgress] = useState<string>('');
  const[inValid, setIsInValid] = useState<boolean>(false);
  const[uploadSuccess, setUploadSuccess] = useState<boolean>(false);



  // const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
  //   setInputValue(e.target.value);
  // };

  const handleFileChange = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setFiles(e.target.files);
    }
  };

  const triggerFileInput = () => {
    const fileInput = document.getElementById('fileInput') as HTMLInputElement;
    if (fileInput) {
      fileInput.click();
    }
  };

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

 

  const handleSubmit = async (e:FormEvent) => {
    e.preventDefault();
    setIsLoading(true)
    if (!files) {
      alert('Please upload the course materials');
      setIsLoading(false)
      return;
    }
  
    const formData = new FormData();
    Array.from(files).forEach((file) => formData.append('files', file));
    // formData.append('chunkSize', chunkSize.toString())
    // formData.append('overlap', overlap.toString())
    setProgress('Uploading To File Storage')
    fetch(`http://127.0.0.1:5000/api/${collectionName}/${domainName}/${username}/createdocument`, {
          method: 'PUT',
           body: formData
      })
    .then(response => {
        if (response.ok) {
          setProgress('Uploading To Vector Store')
          return fetch('http://127.0.0.1:5000/vectorstore', {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({ 
              containername: collectionName,
              chunksize: chunkSize,
              overlap: overlap,
             })
          })
          .then(flaskResponse => {
            if (flaskResponse.ok) {
              console.log('Data loaded into vectorstore successfully:');
              setUploadSuccess(true)
            } 
            else{
              const errorMessage = flaskResponse.text().then(message => {console.log(message)});
              alert(`Internal Server Error: ${flaskResponse.statusText}, Details: ${errorMessage}`);
              throw new Error(`Failed to load into vector store: ${errorMessage}`);      
            }
          })
        } 
        else if(response.status === 400) {
          setIsInValid(true)
        }
        else {
          throw new Error('Failed to create document');
        }
      })
    .finally(() => {
      setIsLoading(false);
      onFileCreated(); 
    });
  };

  useEffect(() => {
    if (uploadSuccess) {
      onClose();
    }
  }, [uploadSuccess, onClose]);
  
  
  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-50">
      <div className="bg-white p-8 rounded-lg shadow-md relative sm:w-2/6 w-5/6">
        {
          !isLoading && (
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
            <p className="text-[#1a2d58] text-center mb-4 font-semibold">{progress}</p>
          </>
        )}
        {
          !isLoading && (
            <>
        <label htmlFor="fileInput" className="block mb-2 text-gray-800 font-semibold">Select Files</label>
        {
          inValid && (
            <p className='text-red-500'> Unsupported file format</p>
          )
        }
        <input
          type="file"
          id="fileInput"
          multiple
          onChange={handleFileChange}
          className="hidden"
        />
        <div className='flex'>
            <button
              type="button"
              className="px-4 py-2 bg-[#1a2d58] text-white rounded-md mr-5 transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C] mb-4"
              onClick={triggerFileInput}
            >
              Choose Files (.docx, .pdf, .pptx, .txt)
            </button>
            {files && (
              <div className="mt-2">
                <FaFileAlt className="text-[#1a2d58] mr-2" />     
              </div>
            )}
        </div>
       
          {/* <label htmlFor="checkbox" className="text-gray-800 font-semibold mr-2 mt-4">Change default chunk size and overlap</label>
          <input
            type="checkbox"
            id="checkbox"
            checked={tick}
            onChange={handleCheckboxChange}
          />
          <p className='text-red-500'> The default chunk size is set to 1000 and overlap is 100</p> */}
{/* 
            {
              showSliders && (
                <>
                <div className="mb-4">
                <label className="block text-[#1a2d58] font-bold mb-2">
                  Chunk Size
                </label>
                <Slider
                  min={1000}
                  max={2000}
                  step={1}
                  value={chunkSize}
                  onChange={handleChunkSliderChange}
                  trackStyle={{ backgroundColor: '#1a2d58' }}
                  handleStyle={{ borderColor: '#1a2d58' }}
                />
                <div className="text-center text-[#1a2d58] font-semibold mt-2">
                  {chunkSize}
                </div>
              </div>
               <div className="mb-4">
               <label className="block text-[#1a2d58] font-bold mb-2">
                 Overlap
               </label>
               <Slider
                 min={100}
                 max={1000}
                 step={1}
                 value={overlap}
                 onChange={handleOverlapSliderChange}
                 trackStyle={{ backgroundColor: '#1a2d58' }}
                 handleStyle={{ borderColor: '#1a2d58' }}
               />
               <div className="text-center text-[#1a2d58] font-semibold mt-2">
                 {overlap}
               </div>
             </div>
             </>
              )
            } */}
            <div>
            <button
          onClick={handleSubmit}
          className="bg-[#2C3463] text-white font-bold py-2 px-4 rounded mt-5 transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]"
        >
          Submit
        </button>

            </div>
        </>

          )
        }
       
      </div>
    </div>
  );
};

export default DocumentPopup;

 // const handleSubmit = async (e: FormEvent) => {
  //   e.preventDefault();
  //   setIsLoading(true);
  
  //   if (!files) {
  //     alert('Please upload the course materials');
  //     setIsLoading(false);
  //     return;
  //   }
  
  //   const formData = new FormData();
  //   Array.from(files).forEach((file) => formData.append('files', file));
  
  //   setProgress('Uploading To File Storage');
  //   fetch(`https://asknarelle-backend.azurewebsites.net/api/${collectionName}/${domainName}/createdocument`, {
  //       method: 'PUT',
  //       body: formData,
  //     })
  //     .then(
  //       response => {
  //         if(response.ok){
  //           setProgress('Uploading To Vector Store');
  //           fetch('http://localhost:5000/vectorstore', {
  //             method: 'PUT',
  //             headers: {
  //               'Content-Type': 'application/json',
  //             },
  //             body: JSON.stringify({
  //               containername: collectionName,
  //               chunksize: chunkSize,
  //               overlap: overlap,
  //           }),
  //         })
  //         .then(
  //             flaskResponse => {
  //               if (flaskResponse.ok) {  
  //                 console.log('Data loaded into vectorstore successfully');
  //                 setUploadSuccess(true);
  //               } else {
  //                 const flaskData = await flaskResponse.json(); 
  //                 const flaskMessage = flaskData.message; // Await the error message
  //                 alert(`Internal Server Error: ${flaskMessage}, Details: ${flaskMessage}`);
  //                 throw new Error(`Failed to load into vector store: ${flaskMessage}`);
  //               }
  //             } 
  //         )
  //       }
  //       else if(!response.ok) {
  //         console.error('Failed to upload document');
  //       }
  //       else if (response.status === 400) {
  //         setIsInValid(true);
  //       } 
  //     })
  //     .catch(error => {
  //       console.error('Error uploading document:', error);
  //     })
  //     .finally (() => {
  //       setIsLoading(false);
  //       onFileCreated();

  //     })
