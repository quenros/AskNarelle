// FileTable.tsx

import React from 'react';


interface Document{
    _id: string;
    uername: string;
    course_name: string;
    domain: string;
    file: string;
    action: string;
    date_str: string;
    time_str: string;
}

interface ActivityTableProps {
  activities: Document[];
}

const ActivityLogTable: React.FC<ActivityTableProps> = ({
  activities,
}) => {
  return (
    <div className="overflow-scroll mt-5">
      <table className="min-w-full divide-y divide-gray-200 rounded-lg">
       <thead className="bg-[#2C3463] sticky top-0 z-10">
          <tr>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              User
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Course
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Category
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              File
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Action
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Date 
            </th>
            <th className="px-6 py-3 text-left text-sm font-medium text-white tracking-wider font-nunito">
              Time
            </th>
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {activities.map((activity: Document, index: number) => (
            <tr key={index}>
              <td className="px-6 py-4 whitespace-nowrap">
              <div className="text-sm text-[#7C8397] font-medium font-nunito">{activity.uername}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{activity.course_name}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{activity.domain}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{activity.file}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{activity.action}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{activity.date_str}</div>
              </td>
              <td className="px-6 py-4 whitespace-nowrap">
                <div className="text-sm text-[#7C8397] font-medium font-nunito">{activity.time_str}</div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ActivityLogTable;