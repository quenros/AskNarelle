import React, { useState } from 'react';
import { Modal, Form, Input, Button, Typography, message, Spin } from 'antd';
import { PublicClientApplication } from '@azure/msal-browser';
import { msalConfig } from '@/authConfig';

interface PopupProps {
  onClose: () => void;
  onDomainCreated: () => void;
  collectionName: string;
}

export const msalInstance = new PublicClientApplication(msalConfig);

const DomainPopup: React.FC<PopupProps> = ({ onClose, onDomainCreated, collectionName }) => {
  const [form] = Form.useForm();
  const [isLoading, setIsLoading] = useState(false);
  const accounts = msalInstance.getAllAccounts();
  const username = accounts?.[0]?.username ?? '';

  const handleSubmit = async () => {
    try {
      const { domainName } = await form.validateFields();
      setIsLoading(true);

      const resp = await fetch('http://localhost:5000/api/createdomain', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          domainName,
          courseName: collectionName,
          user: username,
          action: 'Domain Creation',
        }),
      });

      if (resp.ok) {
        message.success('Domain created successfully');
        onDomainCreated();
        onClose();
      } else if (resp.status === 400) {
        const data = await resp.json().catch(() => ({}));
        const err =
          typeof data?.message === 'string'
            ? data.message
            : 'Failed to create domain';
        message.error(err);
      } else {
        message.error('Failed to create domain');
      }
    } catch (err: any) {
      // ignore form validation errors
      if (!err?.errorFields) {
        message.error(err?.message ?? 'Unknown error');
      }
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Modal
      title="Create Category"
      open
      onCancel={isLoading ? undefined : onClose}
      footer={
        <Button type="primary" onClick={handleSubmit} loading={isLoading}>
          Submit
        </Button>
      }
      maskClosable={!isLoading}
      closable={!isLoading}
      destroyOnClose
    >
      <Typography.Paragraph>
        Create a new category for <b>{collectionName}</b>.
      </Typography.Paragraph>

      <Form form={form} layout="vertical" requiredMark={false}>
        <Form.Item
          label="Category Name"
          name="domainName"
          normalize={(v) => (typeof v === 'string' ? v.trim() : v)}
          rules={[
            { required: true, message: 'Please enter a category name.' },
            {
              pattern: /^[a-z0-9]+$/,
              message: 'Only lowercase letters and numbers are allowed.',
            },
          ]}
        >
          <Input
            placeholder="e.g. machinelearning101"
            disabled={isLoading}
            allowClear
          />
        </Form.Item>
      </Form>

      {isLoading && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <Spin />
          <Typography.Text>Creating…</Typography.Text>
        </div>
      )}
    </Modal>
  );
};

export default DomainPopup;
