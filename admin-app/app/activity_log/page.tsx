"use client"
import { Suspense, useEffect, useState } from 'react';
import { msalConfig } from "@/authConfig";
import { PublicClientApplication} from "@azure/msal-browser";
import withAuth from "../components/authentication/WithAuth";
import ActivityLogTable from '../components/activity_log/ActivityLogTable';

interface Activity{
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


  const[activities, setActivities] = useState<Activity[]>([]);

  useEffect(() => {
    fetch(`http://127.0.0.1:5000/activities/${username}/viewactivities`)
        .then(response => {
          if (!response.ok) {
            throw new Error('Failed to fetch activities');
          }
          return response.json();
        })
        .then((activities: Activity[]) => {
          setActivities(activities)
        })
        .catch(error => {
          console.error('Error fetching collections:', error);
        });

}, [username]); 

  return (
    <main className="flex h-screen mt-[8vh] lg:mt-[0vh] p-10 sm:p-24 bg-gray-100 justify-center">
        <div className="flex flex-row">
            {
                activities?.length > 0 ? (
                    <ActivityLogTable activities={activities}/>

                ) : (
                    <div>
                        No Activities
                    </div>
                )
            }
        </div>    
      </main>
  );
}

const AuthenticatedActivityLog = withAuth(ActivityLog);

export default function ActivityLogsPage(): JSX.Element {
    return (
      <Suspense fallback={<div>Loading...</div>}>
        <AuthenticatedActivityLog/>
      </Suspense>
    );
  }