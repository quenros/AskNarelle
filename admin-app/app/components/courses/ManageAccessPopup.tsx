import React, { useEffect, useState } from 'react'
import { IoIosCloseCircleOutline } from "react-icons/io";
import { Oval } from 'react-loader-spinner';
import { RiDeleteBin6Line } from "react-icons/ri";
import { CgProfile } from "react-icons/cg";

interface PopupProps {
    onClose: () => void;
    courseName: string;
  }

const ManageAccessPopup: React.FC<PopupProps> = ({onClose, courseName}) => {

    const[users, setUsers] = useState<string[]>([]);
    const [isLoading, setIsLoading] = useState<boolean>(false);
    const [errorMessage, setErrorMessage] = useState<string>('');
    const [userDeleted, setUserDeleted] = useState<boolean>(false);

    useEffect(() => {
        fetch(`http://127.0.0.1:5000/manageaccess/${courseName}`)
        .then(response => {
          if (!response.ok) {
            throw new Error('Failed to fetch users');
          }
          return response.json();
        })
        .then((users: string[]) => {
          setUsers(users)
        })
        .catch(error => {
          console.error('Error fetching users:', error);
          setErrorMessage('Error fetching user.')
        });
    }, [courseName, userDeleted]); 

    const handleDeleteUser = (user: string) => {
      setIsLoading(true)
      fetch('http://127.0.0.1:5000/manageaccess/deleteUser', {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ collectionName: courseName, username: user }),
      })
      .then(response => {
        console.log(response);
        setUserDeleted(!userDeleted);
        
      })
      .catch(error => {
        console.error('Error deleting course:', error);
      })
      .finally(() => {
        setIsLoading(false);
    });
  }

  return (
    <div className="fixed inset-0 flex items-center justify-center bg-gray-800 bg-opacity-50 z-50">
      <div className="bg-white p-8 rounded-lg shadow-md relative sm:w-2/6 w-5/6">
        <div className='text-lg font-semibold font-nunito mb-5'>People with access</div>
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
          {users.length > 0 ? (
              <div className="space-y-3">
                  {users.map((user: string, index) => (
                      <div key={index} className="flex justify-between items-center bg-gray-100 p-2 rounded-lg shadow-sm hover:bg-gray-200 mx-5">
                        <div className='flex'>
                        <CgProfile size={24} color='#2C3463'/>
                        <div className="text-gray-800 font-medium px-5 font-nunito">{user}</div>
                        </div>
                          <button onClick={() => handleDeleteUser(user)} className="text-red-500 hover:text-red-700 transition px-5">
                              <RiDeleteBin6Line size={24} />
                          </button>
                      </div>
                  ))}
              </div>
          ) : (
              <p className="text-gray-600 text-center">No users found.</p>
          )}

          {errorMessage && (
              <p className="text-red-500 text-sm mt-4 font-nunito">{errorMessage}</p>
          )}
      </>
        )}
      </div>
    </div>
  )
}

export default ManageAccessPopup