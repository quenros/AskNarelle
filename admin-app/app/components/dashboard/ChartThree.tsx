"use client";
import { ApexOptions } from 'apexcharts';
import React, { useState, useEffect } from 'react';
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
  const [categories, setCategories] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!username) return;

    fetch(`/chats/userSentiments/${username}`)
    .then(response => {
      if (!response.ok) {
        throw new Error('Failed to fetch sentiments');
      }
      return response.json();
    })
    .then((data: { sentiments: string[]; counts: number[] }) => {
      const safeCounts = Array.isArray(data.counts) ? data.counts : [];
      const safeSentiments = Array.isArray(data.sentiments) ? data.sentiments : [];
      
      const newState: ChartThreeState = {
        series: safeCounts
      };
      setCategories(safeSentiments);
      setState(newState);
    })
    .catch(error => {
      console.error("Error fetching chart data:", error);
    })
    .finally(() => {
        setLoading(false);
    });
  }, [username]);

  const options: ApexOptions = {
    chart: {
      fontFamily: 'Satoshi, sans-serif',
      type: 'donut',
    },
    colors: ['#3C50E0', '#6577F3', '#8FD0EF', '#0FADCF'],
    labels: categories, // Using categories for labels in Donut chart
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

  if (loading) {
    return <div className="sm:px-7.5 col-span-12 rounded-sm border border-stroke bg-white px-5 pb-5 pt-7.5 shadow-default xl:col-span-5 h-[350px] flex items-center justify-center">Loading...</div>;
  }
  
  // Handling empty data case for Donut/Pie charts is crucial
  if (state.series.length === 0 || state.series.every(val => val === 0)) {
       return (
        <div className="sm:px-7.5 col-span-12 rounded-sm border border-stroke bg-white px-5 pb-5 pt-7.5 shadow-default xl:col-span-5">
            <div className="mb-3 justify-between gap-4 sm:flex">
                <h5 className="text-xl font-semibold text-[#2C3463] mt-5 font-nunito">
                    Sentiment Analysis
                </h5>
            </div>
            <div className="h-[250px] flex items-center justify-center text-gray-500">
                No sentiment data available.
            </div>
        </div>
       );
  }

  return (
    <div className="sm:px-7.5 col-span-12 rounded-sm border border-stroke bg-white px-5 pb-5 pt-7.5 shadow-default xl:col-span-5">
      <div className="mb-3 justify-between gap-4 sm:flex">
        <div>
          <h5 className="text-xl font-semibold text-[#2C3463] mt-5 font-nunito">
            Sentiment Analysis
          </h5>
        </div>
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

      <div className="flex items-center justify-between flex-wrap gap-y-3">
        {/* Dynamic Legend based on data availability would be better, but keeping static structure for now */}
        {/* Only showing labels that might exist in typical sentiment analysis */}
        <div className="w-full px-8 flex flex-wrap gap-4 justify-center">
             {categories.map((cat, idx) => (
                 <div key={idx} className="flex items-center">
                    <span className="mr-2 block h-3 w-3 rounded-full" style={{backgroundColor: options.colors?.[idx % (options.colors?.length || 1)]}}></span>
                    <p className="text-sm font-medium text-black">{cat}</p>
                 </div>
             ))}
        </div>
      </div>
    </div>
  );
};

export default ChartThree;