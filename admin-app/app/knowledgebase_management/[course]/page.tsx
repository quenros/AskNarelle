"use client"
import { Suspense } from 'react';
import { useState, useEffect} from 'react';
import DomainCard from "../../components/domains/DomainCard";
import { useSearchParams } from 'next/navigation';
import DomainPopup from '../../components/domains/DomainPopup';
import DomainDeletionPopup from '../../components/domains/DomainDeletionPopup';
import { MdDriveFolderUpload } from "react-icons/md";
import withAuth from "../../components/authentication/WithAuth";
import { msalConfig } from "@/authConfig";
import { PublicClientApplication} from "@azure/msal-browser";
import NotFoundPage from '../../components/authentication/404';
import ForbiddenPage from '../../components/authentication/403';

interface Category{
  'domain': string,
  'usertype': string

}
const msalInstance = new PublicClientApplication(msalConfig);

function DomainContent({params} : {params: {course: string}}) {

  const [showPopup, setShowPopup] = useState<boolean>(false);
  const [domainCreated, setDomainCreated] = useState<boolean>(true); 
  const [domains, setDomains] = useState<Category[]>([]);
  const [domainDeleted, setDomainDeleted] = useState<boolean>(true); 
  const[domainName, setDomainName] = useState<string>('')
  const[showDeletionPopup, setShowDeletionPopup] = useState<boolean>(false);
  const[course, setCourse] = useState<string>('');
  const[authorised, setAuthorised] = useState<boolean>(true)
  const[coursePresent, setCoursePresent] = useState<boolean>(true)

  const searchParams = useSearchParams();
  const collectionName = params.course;//searchParams.get("query") || '';

  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username; 

  // const domains = ['Lectures', 'Tutorials', 'Labs'];

  const handleButtonClick = (): void => {
    setShowPopup(true);
  };

  const handleDomainCreated = () => {
    setDomainCreated(!domainCreated);
  };

  const handleDomainDeleted = () => {
    setDomainDeleted(!domainDeleted);
  };

  const handlePressDelete = (courseName: string, domainName: string): void => {
    setCourse(courseName)
    setDomainName(domainName)
    setShowDeletionPopup(true);
  }

  const handleClosePopup = (): void => {
    setShowPopup(false);
  };

  const handleCloseDeletionPopup = (): void => {
    setShowDeletionPopup(false);
  }

  useEffect(() => {
    console.log(collectionName)
    fetch(`https://asknarelle-backend.azurewebsites.net/api/collections/${username}/${collectionName}/domains`)
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
    .then((domains: Category[]) => {
      setDomains(domains);
    })
    .catch(error => {
      console.error('Error fetching collections:', error);
    });
}, [domainCreated, domainDeleted, collectionName, username]); 

  return (
    <main className="flex h-screen mt-[8vh] lg:mt-[0vh] flex-col p-10 sm:p-24 bg-gray-100">   
      <div className="flex flex-row justify-between">
        {
          authorised && coursePresent &&

      <div className="font-semibold relative w-10 text-xl font-nunito">
        Categories
        <div className="absolute left-2 w-full h-1 bg-[#2C3463]"></div>
      </div>
}
       <div>
       {authorised && coursePresent && domains?.length > 0 && <button onClick={handleButtonClick} className="bg-[#2C3463] text-white py-2 px-4 rounded-lg font-normal transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]">Add New Category</button>}
       </div>
      </div>
      {
        coursePresent ? (
           authorised ? (
             domains?.length > 0 ? (
          <div className="flex flex-wrap mt-5">
            {domains?.map((domain: Category, index: number) => (
              <DomainCard key={index} courseName={collectionName} domainName={domain['domain']} onDomainDeleted={handlePressDelete} user_type={domain['usertype']}/>
            ))}
          </div>

        ) : (
          <div className="flex h-screen flex-col items-center justify-center">
          <div className="flex  flex-col bg-white sm:w-4/5 w-full border border-dotted border-[#3F50AD] p-4 mx-auto rounded-lg items-center">
          <MdDriveFolderUpload  size={50} color="#2C3463"/>
          <p className="font-semibold text-lg mt-2 font-nunito">Create a new category</p>
          <button onClick={handleButtonClick} className="bg-[#2C3463] text-white py-2 px-4 rounded-lg font-normal mt-5 sm:w-2/5 w-full  transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C] font-nunito">Add New Folder</button>
          </div>
        </div>
        )
      ) : (
          <ForbiddenPage/>
        )
      ) : (
        <NotFoundPage/>
      )
      }
     
      {showPopup && <DomainPopup onClose={handleClosePopup} onDomainCreated={handleDomainCreated} collectionName = {collectionName}/>}
      {showDeletionPopup && <DomainDeletionPopup onClose={handleCloseDeletionPopup} onCourseDeleted={handleDomainDeleted} courseName= {collectionName} domain={domainName}/>}
    </main>
  );
}

const AuthenticatedDomainContent = withAuth(DomainContent);

export default function DomainPage({params}: {params: {course: string}}): JSX.Element {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AuthenticatedDomainContent params={params}/>
    </Suspense>
  );
}
