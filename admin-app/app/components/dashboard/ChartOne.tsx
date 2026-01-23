"use client";

import React, { useEffect, useState } from 'react';
import { Column } from '@ant-design/plots'; 
import { Card, Spin, Typography } from 'antd';
import { msalConfig } from '../../../authConfig'
import { PublicClientApplication } from '@azure/msal-browser';

const { Title, Text } = Typography;
const msalInstance = new PublicClientApplication(msalConfig);

const ChartOne: React.FC = () => {
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username; 

  const [data, setData] = useState<Array<{ month: string, value: number }>>([]);
  const [loading, setLoading] = useState(true);
  const [totalQueries, setTotalQueries] = useState(0);

  useEffect(() => {
    if (!username) return;

    fetch(`http://localhost:5000/chats/queriesByMonth/${username}`)
    .then(response => {
      if (!response.ok) throw new Error('Failed to fetch data');
      return response.json();
    })
    .then(apiData => {
        const counts = Array.isArray(apiData.counts) ? apiData.counts : [];
        const months = Array.isArray(apiData.months) ? apiData.months : [];
        
        const dataMap: Record<string, number> = {};
        months.forEach((m: string, i: number) => {
            dataMap[m] = counts[i] || 0;
        });

        // Identify unique years from the data
        const years = new Set<number>();
        months.forEach((m: string) => {
            const parts = m.split(' '); // ["January", "2026"]
            if (parts.length > 1) {
                years.add(parseInt(parts[1]));
            }
        });

        // Default to current year if no data
        if (years.size === 0) {
            years.add(new Date().getFullYear());
        }

        const sortedYears = Array.from(years).sort();
        const allMonthsLabels: string[] = [];

        // Generate all "Month Year" combinations for the identified years
        const monthNames = [
            "January", "February", "March", "April", "May", "June", 
            "July", "August", "September", "October", "November", "December"
        ];

        sortedYears.forEach(year => {
            monthNames.forEach(month => {
                allMonthsLabels.push(`${month} ${year}`);
            });
        });

        const chartData = allMonthsLabels.map(label => ({
            month: label,
            value: dataMap[label] || 0
        }));

        setData(chartData);
        setTotalQueries(counts.reduce((a: number, b: number) => a + b, 0));
    })
    .catch(error => console.error("Error:", error))
    .finally(() => setLoading(false));
  }, [username]);

  const config = {
    data,
    xField: 'month',
    yField: 'value',
    color: '#1890ff',
    label: false, 
    xAxis: {
      label: {
        autoHide: false, 
        autoRotate: true,
      },
    },
    tooltip: {
        showMarkers: false
    },
    height: 350,
    autoFit: true, 
  };

  return (
    <Card 
      bordered={false} 
      className="shadow-md" 
      style={{ borderRadius: 8, height: '100%' }}
    >
      <div style={{ marginBottom: 20 }}>
        <Text type="secondary">Total Queries</Text>
        <Title level={3} style={{ margin: 0, color: '#1890ff' }}>
          {totalQueries} queries
        </Title>
      </div>

      {loading ? (
         <div style={{ height: 350, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
            <Spin tip="Loading Chart..." />
         </div>
      ) : (
        // @ts-ignore
         <Column {...config} />
      )}
    </Card>
  );
};

export default ChartOne;