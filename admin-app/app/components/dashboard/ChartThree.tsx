"use client";
import { ApexOptions } from 'apexcharts';
import React, { useState, useEffect } from 'react';
// import ReactApexChart from 'react-apexcharts';
import dynamic from 'next/dynamic';
const ReactApexChart = dynamic(() => import('react-apexcharts'), { ssr: false });

import { msalConfig } from '../../../authConfig'
import { PublicClientApplication } from '@azure/msal-browser';

const msalInstance = new PublicClientApplication(msalConfig);

interface ChartThreeState {
  series: number[];
}


const ChartThree: React.FC = () => {
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username; 
  const [state, setState] = useState<ChartThreeState>({
    series: [],
  });

  const[categories,setCategories] = useState<string[]>([])

  useEffect(() => {
    fetch(`http://127.0.0.1:5000/chats/userSentiments/${username}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to fetch total users');
      }
      return response.json();
    })
    .then((data: { sentiments: string[]; counts: number[] }) => {
      const newState: ChartThreeState = {
        series: data.counts
      };
      setCategories(data.sentiments)
      setState(newState);
    })
    .catch(error => {
      console.error('Error fetching total users:', error);
    });
   }, [username])


  const options: ApexOptions = {
    chart: {
      fontFamily: 'Satoshi, sans-serif',
      type: 'donut',
    },
    colors: ['#3C50E0', '#6577F3', '#8FD0EF', '#0FADCF'],
    labels: categories,
    legend: {
      show: false,
      position: 'bottom',
    },
  
    plotOptions: {
      pie: {
        donut: {
          size: '65%',
          background: 'transparent',
        },
      },
    },
    dataLabels: {
      enabled: false,
    },
    responsive: [
      {
        breakpoint: 2600,
        options: {
          chart: {
            width: 380,
          },
        },
      },
      {
        breakpoint: 640,
        options: {
          chart: {
            width: 200,
          },
        },
      },
    ],
  };

  const handleReset = () => {
    setState((prevState) => ({
      ...prevState,
      series: [65, 34, 12, 56],
    }));
  };
  handleReset;

  return (
    <div className="col-span-12 rounded-sm border border-stroke bg-white px-5 pt-7.5 pb-5 shadow-md w-full sm:px-7.5 xl:col-span-8">
        <div className='flex justify-center'>
          <h5 className="font-semibold text-[#2C3463] mt-5 font-nunito">
            Sentiment Analysis
          </h5>
        </div>
  
      <div className="mb-2">
        <div id="chartThree" className="mx-auto flex justify-center">
          <ReactApexChart
            options={options}
            series={state.series}
            type="donut"
          />
        </div>
      </div>

      <div className="flex items-center justify-between flex-wrap">
        <div className="sm:w-1/4 w-full px-8">
          <div className="flex w-full items-center">
            <span className="mr-2 block h-3 w-full max-w-3 rounded-full bg-[#3C50E0]"></span>
            <p className="text-sm font-medium text-black">
               Positive 
            </p>
          </div>
        </div>
        <div className="sm:w-1/4 w-full px-8">
          <div className="flex w-full items-center">
            <span className="mr-2 block h-3 w-full max-w-3 rounded-full bg-[#6577F3]"></span>
            <p className="text-sm font-medium text-black">
              Negative 
            </p>
          </div>
        </div>
        <div className="sm:w-1/4 w-full px-8">
          <div className="flex w-full items-center">
            <span className="mr-2 block h-3 w-full max-w-3 rounded-full bg-[#0FADCF]"></span>
            <p className=" text-sm font-medium text-black">
               Neutral
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ChartThree;
