"use client";
import { ApexOptions } from 'apexcharts';
import dynamic from 'next/dynamic';
import React, { useEffect, useState } from 'react';
// import ReactApexChart from 'react-apexcharts';
const ReactApexChart = dynamic(() => import('react-apexcharts'), { ssr: false });
import { msalConfig } from '../../../authConfig'
import { PublicClientApplication } from '@azure/msal-browser';

const msalInstance = new PublicClientApplication(msalConfig);


interface ChartOneState {
  // series: {
  //   name: string;
  //   data: number[];
  // }[];
  series: {
    name: string,
    data: number[]
  }[];
}

const ChartOne: React.FC = () => {

  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username; 

  const [state, setState] = useState<ChartOneState>({
    series: [
    {
      name: "Number of queries by month",
      data: []
    },
  ],
});
const[categories, setCategories] = useState<string[]>([])

  useEffect(() => {
    fetch(`http://localhost:5000/chats/queriesByMonth/${username}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to fetch total users');
      }
      return response.json();
    })
    .then((data: { months: string[]; counts: number[] }) => {
      const newState: ChartOneState = {
        series: [
          {
            name: "Number of queries by month",
            data : data.counts
          }
        ]
      };
      setCategories(data.months)
      setState(newState);
    })
    .catch(error => {
      console.error('Error fetching total users:', error);
    });
   }, [username])

  const options: ApexOptions = {
    legend: {
      show: false,
      position: 'top',
      horizontalAlign: 'left',
    },
    colors: ['#3C50E0', '#80CAEE'],
    chart: {
      fontFamily: 'Satoshi, sans-serif',
      height: 335,
      type: 'area',
      dropShadow: {
        enabled: true,
        color: '#623CEA14',
        top: 10,
        blur: 4,
        left: 0,
        opacity: 0.1,
      },
  
      toolbar: {
        show: false,
      },
    },
    responsive: [
      {
        breakpoint: 1024,
        options: {
          chart: {
            height: 300,
          },
        },
      },
      {
        breakpoint: 1366,
        options: {
          chart: {
            height: 350,
          },
        },
      },
    ],
    stroke: {
      width: [2, 2],
      curve: 'straight',
    },
    // labels: {
    //   show: false,
    //   position: "top",
    // },
    grid: {
      xaxis: {
        lines: {
          show: true,
        },
      },
      yaxis: {
        lines: {
          show: true,
        },
      },
    },
    dataLabels: {
      enabled: false,
    },
    markers: {
      size: 4,
      colors: '#fff',
      strokeColors: ['#3056D3', '#80CAEE'],
      strokeWidth: 3,
      strokeOpacity: 0.9,
      strokeDashArray: 0,
      fillOpacity: 1,
      discrete: [],
      hover: {
        size: undefined,
        sizeOffset: 5,
      },
    },
    xaxis: {
      type: 'category',
      categories: categories,
      axisBorder: {
        show: false,
      },
      axisTicks: {
        show: false,
      },
    },
    yaxis: {
      title: {
        style: {
          fontSize: '0px',
        },
      },
      min: 0,
      max: 10,
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
      <div className="flex flex-wrap items-start justify-between gap-3 sm:flex-nowrap">
        <div className="flex w-full flex-wrap gap-3 sm:gap-5 justify-center">
          <p className="font-semibold text-[#2C3463] mt-5 font-nunito">Number of queries by month</p> 
        </div>
      </div>

      <div>
        <div id="chartOne" className="-ml-5">
          <ReactApexChart
            options={options}
            series={state.series}
            type="area"
            height={350}
          />
        </div>
      </div>
    </div>
  );
};

export default ChartOne;
