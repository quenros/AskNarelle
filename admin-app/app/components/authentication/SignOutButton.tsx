'use client';

import React, { useState } from 'react';
import { Button, Popconfirm } from 'antd';
import { LogoutOutlined } from '@ant-design/icons';
import { msalInstance } from '@/app/_app';
import { useRouter } from 'next/navigation';

export default function SignOutButton() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const handleLogout = (logoutType: string) => {
    if (logoutType === 'popup') {
      setLoading(true);
      msalInstance.logoutPopup().then(() => {
        router.push('/');
      }).catch((e) => {
        console.error(`logoutPopup failed: ${e}`);
      }).finally(() => setLoading(false));
    } else if (logoutType === 'redirect') {
      msalInstance.logoutRedirect().catch((e) => {
        console.error(`logoutRedirect failed: ${e}`);
      });
    }
  };

  return (
<Popconfirm
  placement="bottomRight"
  title="Confirm Logout"
  description="Are you sure you want to log out?"
  trigger="click"
  okText="Yes"
  cancelText="Cancel"
  okButtonProps={{
    size: 'small',
    style: {
      fontSize: 12,
      lineHeight: 1.2,
      padding: '4px 16px',
    },
  }}
  cancelButtonProps={{
    size: 'small',
    style: {
      fontSize: 12,
      lineHeight: 1.2,
      padding: '4px 16px',
    },
  }}
  onConfirm={() => handleLogout('popup')}
>
  <Button type="primary" danger icon={<LogoutOutlined />} loading={loading}>
    Log Out
  </Button>
</Popconfirm>


  );

}
