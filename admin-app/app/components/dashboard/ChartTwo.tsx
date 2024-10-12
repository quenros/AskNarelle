"use client";
import { ApexOptions } from 'apexcharts';
import React, { useState, useEffect } from 'react';
// import ReactApexChart from 'react-apexcharts';
const ReactApexChart = dynamic(() => import('react-apexcharts'), { ssr: false });
import dynamic from 'next/dynamic';

import { msalConfig } from '../../../authConfig'
import { PublicClientApplication } from '@azure/msal-browser';

const msalInstance = new PublicClientApplication(msalConfig);

interface ChartTwoState {
  series: {
    name: string;
    data: number[];
  }[];
}

const ChartTwo: React.FC = () => {
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username; 
  const [state, setState] = useState<ChartTwoState>({
    series: [
      {
        name: 'Number of queries by course',
        data: [],
      },
    ],
  });
  const[categories,setCategories] = useState<string[]>([])

  useEffect(() => {
    fetch(`http://127.0.0.1:5000/chats/queriesByCourse/${username}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to fetch total users');
      }
      return response.json();
    })
    .then((data: { courses: string[]; counts: number[] }) => {
      const newState: ChartTwoState = {
        series: [
          {
            name: "Number of queries by course",
            data : data.counts
          }
        ]
      };
      setCategories(data.courses)
      setState(newState);
    })
    .catch(error => {
      console.error('Error fetching total users:', error);
    });
   }, [username])

   const options: ApexOptions = {
    colors: ['#3C50E0', '#80CAEE'],
    chart: {
      fontFamily: 'Satoshi, sans-serif',
      type: 'bar',
      height: 335,
      stacked: true,
      toolbar: {
        show: false,
      },
      zoom: {
        enabled: false,
      },
    },
  
    responsive: [
      {
        breakpoint: 1536,
        options: {
          plotOptions: {
            bar: {
              borderRadius: 0,
              columnWidth: '25%',
            },
          },
        },
      },
    ],
    plotOptions: {
      bar: {
        horizontal: false,
        borderRadius: 0,
        columnWidth: '25%',
        borderRadiusApplication: 'end',
        borderRadiusWhenStacked: 'last',
      },
    },
    dataLabels: {
      enabled: false,
    },
  
    xaxis: {
      categories: categories,
    },
    legend: {
      position: 'top',
      horizontalAlign: 'left',
      fontFamily: 'Satoshi',
      fontWeight: 500,
      fontSize: '14px',
  
    },
    fill: {
      opacity: 1,
    },
  };
  
  const handleReset = () => {
    setState((prevState) => ({
      ...prevState,
    }));
  };
  handleReset;  

  return (
    <div className="col-span-12 rounded-sm border border-stroke bg-white px-5 pt-7.5 pb-5 shadow-md w-full sm:px-7.5 xl:col-span-8">
    <div className="mb-4 justify-between gap-4 sm:flex">
    <div className="flex w-full flex-wrap gap-3 sm:gap-5 justify-center">
          <p className="font-semibold text-[#2C3463] mt-5 font-nunito">Number of queries by course</p> 
        </div>
    </div>

    <div>
      <div id="chartTwo" className="-ml-5 -mb-9">
        <ReactApexChart
          options={options}
          series={state.series}
          type="bar"
          height={350}
        />
      </div>
    </div>
  </div>
  );
};

export default ChartTwo;
