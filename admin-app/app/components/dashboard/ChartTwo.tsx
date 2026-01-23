"use client";

import React, { useState, useEffect } from 'react';
import { Column } from '@ant-design/plots'; 
import { Card, Spin, Typography } from 'antd';
import { msalConfig } from '../../../authConfig'
import { PublicClientApplication } from '@azure/msal-browser';

const { Title } = Typography;
const msalInstance = new PublicClientApplication(msalConfig);

const ChartTwo: React.FC = () => {
  const accounts = msalInstance.getAllAccounts();
  const username = accounts[0]?.username; 
  
  const [data, setData] = useState<Array<{ course: string, queries: number }>>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!username) return;

    fetch(`http://localhost:5000/chats/queriesByCourse/${username}`)
    .then(response => {
      if (!response.ok) throw new Error('Failed to fetch data');
      return response.json();
    })
    .then(apiData => {
      const counts = Array.isArray(apiData.counts) ? apiData.counts : [];
      const courses = Array.isArray(apiData.courses) ? apiData.courses : [];

      const chartData = courses.map((course: string, index: number) => ({
          course: course,
          queries: counts[index] || 0
      }));

      setData(chartData);
    })
    .catch(error => console.error("Error:", error))
    .finally(() => setLoading(false));
  }, [username]);

  const config = {
    data,
    xField: 'course',
    yField: 'queries',
    color: '#1890ff',
    label: false, 
    xAxis: {
      label: {
        autoHide: true,
        autoRotate: false,
      },
    },
    tooltip: {
        showMarkers: false
    },
    height: 350,
    width: 250,
    autoFit: false,
  };
  
  return (
    <Card 
      bordered={false} 
      className="shadow-md" 
      style={{ borderRadius: 8, height: '100%' }}
    >
      <div style={{ marginBottom: 20 }}>
        <Title level={4} style={{ margin: 0, color: '#2C3463' }}>
          Queries by Course
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

export default ChartTwo;