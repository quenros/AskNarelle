"use client"
import { Suspense, useEffect, useState } from 'react';
import { msalConfig } from "@/authConfig";
import { PublicClientApplication} from "@azure/msal-browser";
import withAuth from "../components/authentication/WithAuth";
import ActivityLogTable from '../components/activity_log/ActivityLogTable';
import { CiSearch } from "react-icons/ci";
import ForbiddenPage from '../components/authentication/403';
import DatePicker from 'react-datepicker';
import 'react-datepicker/dist/react-datepicker.css';

interface Activity {
    _id: string;
    uername: string;
    course_name: string;
    domain: string;
    file: string;
    action: string;
    date_str: string;
    time_str: string;
}

const msalInstance = new PublicClientApplication(msalConfig);

function ActivityLog(): JSX.Element {
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username;
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [searchUsername, setSearchUsername] = useState<string>('');
  const [searchCourseName, setSearchCourseName] = useState<string>('');
  const [searchDomain, setSearchDomain] = useState<string>('');
  const [actionType, setActionType] = useState<string | null>(null);
  const [startDate, setStartDate] = useState<Date | null>(null);
  const [endDate, setEndDate] = useState<Date | null>(null);
  const [authorised, setAuthorised] = useState<boolean>(true);
  const [activities, setActivities] = useState<Activity[]>([]);

  const handleSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(event.target.value);
  };

  const handleUsernameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchUsername(event.target.value);
  };

  const handleCourseNameChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchCourseName(event.target.value);
  };

  const handleDomainChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setSearchDomain(event.target.value);
  };

  useEffect(() => {
    fetch(`http://localhost:5000/activities/${username}/viewactivities`)
      .then(response => {
        if (response.status === 403) {
          setAuthorised(false);
        } else if (response.status === 500) {
          throw new Error('Failed to fetch activities');
        } else {
          return response.json();
        }
      })
      .then((activities: Activity[]) => {
        setActivities(activities);
      })
      .catch(error => {
        console.error('Error fetching activities:', error);
      });
  }, [username]);

  // Filter activities based on search queries and date range
  const filteredActivities = activities?.filter(document =>
    document?.file?.toLowerCase().includes(searchQuery.toLowerCase()) &&
    document?.uername?.toLowerCase().includes(searchUsername.toLowerCase()) &&
    document?.course_name?.toLowerCase().includes(searchCourseName.toLowerCase()) &&
    document?.domain?.toLowerCase().includes(searchDomain.toLowerCase()) &&
    (!actionType || document.action === actionType) &&  
    (!startDate || new Date(document.date_str) >= startDate) &&
    (!endDate || new Date(document.date_str) <= endDate)
  );

  return (
    <main className="flex flex-col h-screen lg:mt-[0vh] p-10 sm:p-24">
      {authorised ? (
        activities.length > 0 ? (
          <>
            <div className='flex justify-between mt-5 sm:mt-0 w-full'>
              <div className='flex flex-col w-1/3'>
                <div className='flex justify-between'>
                  {/* Search Box for Username */}
                  <div className='flex flex-col'>
                    <label htmlFor="searchUsername" className="block mb-2 font-bold font-nunito text-gray-800">Username</label>
                    <div className="relative">
                      <input
                        type="text"
                        value={searchUsername}
                        onChange={handleUsernameChange}
                        placeholder="Username"
                        className="border border-gray-300 rounded-lg py-2 pl-10 pr-4 mr-2 w-3/4 font-nunito"
                      />
                      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                        <CiSearch size={20} />
                      </div>
                    </div>
                  </div>

                  {/* Search Box for Course Name */}
                  <div className='flex flex-col'>
                    <label htmlFor="searchCoursename" className="block mb-2 font-bold font-nunito text-gray-800">Course</label>
                    <div className="relative">
                      <input
                        type="text"
                        value={searchCourseName}
                        onChange={handleCourseNameChange}
                        placeholder="Course Name"
                        className="border border-gray-300 rounded-lg py-2 pl-10 pr-4 mr-2 w-3/4 font-nunito"
                      />
                      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                        <CiSearch size={20} />
                      </div>
                    </div>
                  </div>
                </div>

                <div className='mt-5 flex justify-between'>
                  {/* Search Box for Domain */}
                  <div className='flex flex-col'>
                    <label htmlFor="searchDomain" className="block mb-2 font-bold font-nunito text-gray-800">Category</label>
                    <div className="relative">
                      <input
                        type="text"
                        value={searchDomain}
                        onChange={handleDomainChange}
                        placeholder="Category"
                        className="border border-gray-300 rounded-lg py-2 pl-10 pr-4 mr-2 w-3/4 font-nunito"
                      />
                      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                        <CiSearch size={20} />
                      </div>
                    </div>
                  </div>

                  {/* Search Box for File */}
                  <div className='flex flex-col'>
                    <label htmlFor="searchFile" className="block mb-2 font-bold font-nunito text-gray-800">File</label>
                    <div className="relative">
                      <input
                        type="text"
                        value={searchQuery}
                        onChange={handleSearchChange}
                        placeholder="File Name"
                        className="border border-gray-300 rounded-lg py-2 pl-10 pr-4 mr-2 w-3/4 font-nunito"
                      />
                      <div className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
                        <CiSearch size={20} />
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Date Filters */}
              <div className='flex flex-col'>
              <div>
              <label className="block mb-2 font-bold font-nunito text-gray-800">
                Action Type
              </label>
              <select
                className="block w-[50] p-2 text-base border border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500"
                value={actionType || ''}
                onChange={(e) =>
                  setActionType(
                    e.target.value === '' ? null : e.target.value
                  )
                }
              >
                <option value="">All</option>
                <option value="Domain Creation">Domain Creation</option>
                <option value="Uploaded File">Uploaded File</option>
                <option value="Moved to vector store">Moved to vector store</option>
                <option value="File Deletion">File Deletion</option>
              </select>
          </div>
          <div className='flex mt-5 z-20'>
          <div className='mr-5'>
                  <label className="block mb-2 font-bold font-nunito text-gray-800">Start Date</label>
                  <DatePicker
                    selected={startDate}
                    onChange={(date) => setStartDate(date)}
                    dateFormat="yyyy-MM-dd"
                    className="mt-1 p-2 border border-gray-300 rounded-md"
                    placeholderText="Select start date"
                  />
                </div>
                <div>
                  <label className="block mb-2 font-bold font-nunito text-gray-800">End Date</label>
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
            </div>

            <ActivityLogTable activities={filteredActivities} />
          </>
        ) : (
          <div className="flex h-screen flex-col items-center justify-center">
            <div className="flex flex-col bg-white sm:w-4/5 w-full border border-dotted border-[#3F50AD] p-4 mx-auto rounded-lg items-center">
              No Activities Logged
            </div>
          </div>
        )
      ) : (
        <ForbiddenPage />
      )}
    </main>
  );
}

const AuthenticatedActivityLog = withAuth(ActivityLog);

export default function ActivityLogsPage(): JSX.Element {
  return (
    <Suspense fallback={<div>Loading...</div>}>
      <AuthenticatedActivityLog />
    </Suspense>
  );
}
