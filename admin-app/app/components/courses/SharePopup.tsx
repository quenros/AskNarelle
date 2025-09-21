import React, { useState } from 'react';
import { Modal, Form, Input, Button, Spin, Typography, message } from 'antd';
import { MailOutlined } from '@ant-design/icons';
import { PublicClientApplication, AccountInfo } from '@azure/msal-browser';
import { msalConfig } from '@/authConfig';

interface PopupProps {
  onClose: () => void;
  onCourseShared: () => void;
  courseName: string;
}

export const msalInstance = new PublicClientApplication(msalConfig);

const SharePopup: React.FC<PopupProps> = ({ onClose, onCourseShared, courseName }) => {
  const [form] = Form.useForm();
  const [isLoading, setIsLoading] = useState(false);
  const [open] = useState(true); // always shown when mounted; parent unmounts to close
  const accounts: AccountInfo[] = msalInstance.getAllAccounts();
  const username = accounts?.[0]?.username ?? '';

  const handleInvite = async () => {
    try {
      const { email } = await form.validateFields();
      setIsLoading(true);

      const resp = await fetch('http://localhost:5000/invite', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, course: courseName }),
      });

      const result = await resp.json();
      if (resp.ok) {
        message.success('Invitation sent successfully!');
        onCourseShared();
        onClose();
      } else {
        const errMsg = typeof result?.error === 'string'
          ? result.error
          : JSON.stringify(result?.error ?? 'Unknown error');
        message.error(errMsg);
      }
    } catch (err) {
      // validation errors are thrown by form; ignore those
      if ((err as any)?.errorFields) return;
      message.error(err instanceof Error ? err.message : 'An unknown error occurred.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      title="Share course"
      open={open}
      onCancel={onClose}
      footer={
        <Button type="primary" onClick={handleInvite} loading={isLoading}>
          Invite
        </Button>
      }
      destroyOnClose
      maskClosable={!isLoading}
    >
      <Typography.Paragraph>
        Enter the user’s NTU email to send an invite for <b>{courseName}</b>.
      </Typography.Paragraph>

      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item
          label="User Email"
          name="email"
          rules={[
            { required: true, message: 'Please enter an email.' },
            { type: 'email', message: 'Please enter a valid email.' },
            // If you want to enforce NTU emails, uncomment:
            // { pattern: /@ntu\.edu\.sg$/i, message: 'Only NTU emails are allowed.' },
          ]}
        >
          <Input
            prefix={<MailOutlined />}
            placeholder="Enter NTU email"
            autoFocus
            disabled={isLoading}
            allowClear
          />
        </Form.Item>
      </Form>

      {isLoading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Spin />
          <Typography.Text>Sending…</Typography.Text>
        </div>
      )}
    </Modal>
  );
};

export default SharePopup;
